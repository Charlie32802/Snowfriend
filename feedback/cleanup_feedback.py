"""
Management command to clean up old feedback submissions.
Run this periodically via cron job or Django-Q/Celery.

Usage:
    python manage.py cleanup_feedback
    python manage.py cleanup_feedback --days 90
    python manage.py cleanup_feedback --dry-run
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from feedback.models import Feedback
import logging

logger = logging.getLogger('feedback.validation')


class Command(BaseCommand):
    help = 'Clean up old feedback submissions for GDPR compliance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete feedback older than this many days (default: 90)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        threshold = timezone.now() - timedelta(days=days)
        
        # Get old submissions
        old_submissions = Feedback.objects.filter(created_at__lt=threshold)
        count = old_submissions.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'No feedback older than {days} days found.'
                )
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} feedback submission(s) older than {days} days'
                )
            )
            
            # Show some examples
            examples = old_submissions[:5]
            self.stdout.write('\nExamples of what would be deleted:')
            for feedback in examples:
                self.stdout.write(
                    f'  - ID {feedback.feedback_id}: {feedback.rating} stars, '
                    f'created {feedback.created_at.strftime("%Y-%m-%d")}'
                )
            
            if count > 5:
                self.stdout.write(f'  ... and {count - 5} more')
        
        else:
            # Confirm deletion
            self.stdout.write(
                self.style.WARNING(
                    f'\nAbout to delete {count} feedback submission(s) older than {days} days'
                )
            )
            
            confirm = input('Are you sure you want to proceed? (yes/no): ')
            
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Deletion cancelled.'))
                return
            
            # Perform deletion
            deleted_count, _ = old_submissions.delete()
            
            logger.info(f'Cleaned up {deleted_count} old feedback submissions (>{days} days)')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully deleted {deleted_count} feedback submission(s)'
                )
            )