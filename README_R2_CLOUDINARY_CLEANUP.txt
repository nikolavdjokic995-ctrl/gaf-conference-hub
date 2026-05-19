R2/Cloudinary cleanup fix

Zameni fajlove iz ZIP-a preko postojećih fajlova u projektu.

Najvažnije izmene:
- uklonjeni su svi cloudinary_storage importi iz migration fajlova
- uklonjeni su storage=cloudinary_storage... argumenti iz starih migracija
- vraćen je ispravan 0024_submission_revision_workflow.py
- slučajno kreirani 0024_submission_revision_workflow_fixed.py je pretvoren u no-op migraciju da ne pravi duplicate-field problem
- settings.py sada ima "storages" u INSTALLED_APPS

Posle zamene fajlova:
git add .
git commit -m "Clean Cloudinary references for R2 deployment"
git push
