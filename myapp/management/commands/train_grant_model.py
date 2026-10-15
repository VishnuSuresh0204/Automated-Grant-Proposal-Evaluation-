from django.core.management.base import BaseCommand, CommandError
from myapp.ml_model import train_grant_score_model


class Command(BaseCommand):
    help = "Train the grant proposal ML model"

    def handle(self, *args, **options):
        try:
            result = train_grant_score_model()
        except (ValueError, FileNotFoundError) as error:
            raise CommandError(str(error)) from error

        self.stdout.write(
            self.style.SUCCESS("Model trained successfully!")
        )
        self.stdout.write(f"MAE: {result['mae']:.3f}")
        self.stdout.write(f"RMSE: {result['rmse']:.3f}")
        self.stdout.write(f"R²: {result['r2']}")