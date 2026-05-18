from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from payroll.utils import repair_fk_on_delete_rules
import re

class Command(BaseCommand):
    help = 'Audits and repairs PostgreSQL foreign key ON DELETE rules to match ORM models.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--lock-timeout',
            default='10s',
            help='PostgreSQL lock timeout (e.g. 10s, 30s)'
        )
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Raise error if any constraints cannot be repaired due to lock timeouts'
        )
        parser.add_argument(
            '--apps',
            nargs='+',
            default=['payroll', 'payees', 'configs', 'core', 'zohopeople'],
            help='List of apps to audit'
        )

    def handle(self, *args, **options):
        # argparse converts '--lock-timeout' to 'lock_timeout'

        lock_timeout = options['lock_timeout']
        if not re.match(r'^\d+(ms|s|min)?$', lock_timeout):
            raise CommandError("Invalid lock-timeout format. Use format like '10s', '30s', '500ms'.")

        strict = options['strict']
        target_apps = options['apps']
        
        repaired_count, skipped_fks, unvalidated_fks = repair_fk_on_delete_rules(
            apps_registry=apps, 
            target_apps=target_apps, 
            lock_timeout=lock_timeout, 
            strict=strict, 
            stdout=self.stdout
        )
        
        if repaired_count is None:
            return

        if skipped_fks or unvalidated_fks:
            self.stdout.write(self.style.WARNING(
                f"\nRepair completed with warnings:\n"
                f"- Repaired: {repaired_count}\n"
                f"- Skipped (timeout): {len(skipped_fks)}\n"
                f"- Unvalidated (timeout): {len(unvalidated_fks)}\n"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\nSuccessfully repaired and validated {repaired_count} constraint(s)."
            ))
