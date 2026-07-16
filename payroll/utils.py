import logging

from django.contrib import messages
from django.db import connection as default_connection, models
from django.db.utils import OperationalError
from payees.constants import MONTH_CHOICES

logger = logging.getLogger(__name__)


def check_single_payrun_selection(queryset, modeladmin, request):
    """
   Checks if exactly one item is selected in the queryset.
   Displays an error message if not.
   Returns True if exactly one item is selected, False otherwise.
   """
    if queryset[1:2].exists():
        modeladmin.message_user(
            request,
            "Please select only one payrun entry at a time. Multiple "
            "selections are not allowed to ensure accurate processing.",
            level=messages.ERROR
        )
        return False
    return True


def check_latest_payrun(modeladmin, request, selected_payrun, latest_payrun):
    """
    Ensure that a selected payrun entry is the most recent one before
    proceeding with an action in an administrative interface.
    """
    if selected_payrun == latest_payrun:
        return True

    modeladmin.message_user(
        request,
        "To proceed, please select the most recent payrun entry.",
        level=messages.ERROR
    )
    return False


def get_latest_payrun():
    from .models import PayRun

    return PayRun.objects.order_by('-year', '-month', '-created_at').first()


def get_month_name(month):
    """
    Retrieve the name of the month corresponding to the given month integer.
    """

    month_names = dict(MONTH_CHOICES)
    return month_names.get(month)


def repair_fk_on_delete_rules(apps_registry, target_apps, lock_timeout='10s', strict=False, stdout=None, connection=None):
    """
    Audits and repairs PostgreSQL foreign key ON DELETE rules to match the provided apps_registry.
    apps_registry can be the historical 'apps' from a migration or the current 'django.apps'.
    """
    conn = connection or default_connection
    if conn.vendor != 'postgresql':
        if stdout:
            stdout.write("Skipping: Not a PostgreSQL database.")
        return None, [], []

    with conn.cursor() as cursor:
        # Capture old timeout to restore later
        cursor.execute("SHOW lock_timeout")
        old_timeout = cursor.fetchone()[0]

        skipped_fks = []
        unvalidated_fks = []
        repaired_count = 0

        try:
            # Set lock timeout for this session
            cursor.execute("SET lock_timeout = %s", [lock_timeout])
            
            # Precompute existing tables
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()")
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            for app_name in target_apps:
                try:
                    app_config = apps_registry.get_app_config(app_name)
                except LookupError:
                    continue
                    
                for model in app_config.get_models():
                    if model._meta.proxy:
                        continue

                    table_name = model._meta.db_table
                    if table_name not in existing_tables:
                        continue

                    # Audit existing FKs
                    cursor.execute("""
                        SELECT 
                            kcu.column_name, 
                            rc.delete_rule,
                            tc.constraint_name,
                            rc.update_rule,
                            tc.is_deferrable,
                            tc.initially_deferred
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu 
                        ON tc.constraint_name = kcu.constraint_name AND tc.constraint_schema = kcu.constraint_schema
                    JOIN information_schema.referential_constraints AS rc 
                        ON tc.constraint_name = rc.constraint_name AND tc.constraint_schema = rc.constraint_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = %s AND tc.table_schema = current_schema()
                    """, [table_name])
                    existing_fks = {row[0]: row[1:] for row in cursor.fetchall()}
                    
                    for field in model._meta.local_fields:
                        remote_field = getattr(field, 'remote_field', None)
                        if remote_field is None or not getattr(field, 'db_constraint', True):
                            continue

                        on_delete_behavior = getattr(field.remote_field, "on_delete", None)
                        expected_delete_rule = "NO ACTION"
                        if on_delete_behavior == models.SET_NULL:
                            expected_delete_rule = "SET NULL"
                        elif on_delete_behavior == models.CASCADE:
                            expected_delete_rule = "CASCADE"
                        elif on_delete_behavior == models.SET_DEFAULT:
                            expected_delete_rule = "SET DEFAULT"
                        elif on_delete_behavior == models.PROTECT or (hasattr(models, 'RESTRICT') and on_delete_behavior == models.RESTRICT):
                            expected_delete_rule = "RESTRICT"

                        if field.column not in existing_fks:
                            continue

                        d_rule, c_name, u_rule, is_def, init_def = existing_fks[field.column]
                        if d_rule == expected_delete_rule:
                            continue

                        target_table = field.target_field.model._meta.db_table
                        target_column = field.target_field.column
                        if target_table not in existing_tables:
                            continue

                        defer_sql = ""
                        if is_def == 'YES':
                            defer_sql = f" DEFERRABLE INITIALLY {'DEFERRED' if init_def == 'YES' else 'IMMEDIATE'}"

                        # SQL identifiers (table/column/constraint names) cannot be
                        # parameterised with %s placeholders — only values can.
                        # quote_name() wraps each identifier in double-quotes and
                        # escapes internal double-quotes, which is the correct
                        # PostgreSQL defence against identifier injection.
                        # All identifiers here are sourced from Django _meta or
                        # information_schema, not from user input, so injection
                        # risk is absent regardless of the quoting.
                        sql = (
                            f"ALTER TABLE {conn.ops.quote_name(table_name)} "
                            f"DROP CONSTRAINT {conn.ops.quote_name(c_name)}, "
                            f"ADD CONSTRAINT {conn.ops.quote_name(c_name)} "
                            f"FOREIGN KEY ({conn.ops.quote_name(field.column)}) "
                            f"REFERENCES {conn.ops.quote_name(target_table)} ({conn.ops.quote_name(target_column)}) "
                            f"ON DELETE {expected_delete_rule} ON UPDATE {u_rule}{defer_sql} NOT VALID"
                        )
                        try:
                            cursor.execute(sql)
                            try:
                                cursor.execute(f"ALTER TABLE {conn.ops.quote_name(table_name)} VALIDATE CONSTRAINT {conn.ops.quote_name(c_name)}")
                            except OperationalError as val_e:
                                is_lock_timeout = getattr(val_e, 'pgcode', None) == '55P03' or 'lock timeout' in str(val_e).lower()
                                if is_lock_timeout:
                                    if stdout:
                                        stdout.write(f"Repaired but unvalidated (timeout): {table_name}.{field.column}")
                                    logger.warning("Skipped FK validation for %s.%s due to lock timeout.", table_name, field.column)
                                    unvalidated_fks.append(f"{table_name}.{field.column}")
                                else:
                                    raise
                            else:
                                if stdout:
                                    stdout.write(f"Repaired: {table_name}.{field.column} -> {expected_delete_rule}")

                            repaired_count += 1
                        except OperationalError as e:
                            is_lock_timeout = getattr(e, 'pgcode', None) == '55P03' or 'lock timeout' in str(e).lower()
                            if is_lock_timeout:
                                if stdout:
                                    stdout.write(f"Skipped (timeout): {table_name}.{field.column}")
                                logger.warning("Skipped FK repair for %s.%s due to lock timeout.", table_name, field.column)
                                skipped_fks.append(f"{table_name}.{field.column}")
                                continue
                            raise
        finally:
            cursor.execute("SET lock_timeout = %s", [old_timeout])
        
        if strict and (skipped_fks or unvalidated_fks):
            details = []
            if skipped_fks:
                details.append(f"{len(skipped_fks)} skipped ({', '.join(skipped_fks)})")
            if unvalidated_fks:
                details.append(f"{len(unvalidated_fks)} unvalidated ({', '.join(unvalidated_fks)})")
            raise RuntimeError(f"Strict mode enabled: " + "; ".join(details) + " due to lock timeouts.")
        
        return repaired_count, skipped_fks, unvalidated_fks
