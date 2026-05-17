from pathlib import Path

from django.core.files import File


def save_local_file_to_field(field_file, local_path, storage_name):
    """Save a local temporary file to the model FileField's configured storage.

    The storage is HybridDocumentStorage, so it tries Supabase first and falls back
    to Cloudinary if Supabase is unavailable/full.
    """
    with open(local_path, "rb") as handle:
        field_file.save(storage_name, File(handle), save=False)


def clear_file_field(field_file, save_instance=False):
    if not field_file:
        return False

    try:
        field_file.delete(save=save_instance)
        return True
    except Exception as exc:
        print("Could not delete stored file:", exc)
        try:
            field_file.name = ""
        except Exception:
            pass
        return False


def cleanup_submission_temporary_files(submission):
    """Delete temporary files when a submission reaches final acceptance.

    Kept permanently:
    - current full_paper_file / latest author version
    - revised_paper_file if it exists
    - final_publication_file

    Removed:
    - anonymized reviewer copy
    - reviewer commented uploads
    - intermediate layout revised file
    """
    deleted = 0

    if submission.anonymized_paper_file:
        if clear_file_field(submission.anonymized_paper_file, save_instance=False):
            deleted += 1
        submission.anonymized_paper_file = None

    if submission.layout_revised_paper_file:
        if clear_file_field(submission.layout_revised_paper_file, save_instance=False):
            deleted += 1
        submission.layout_revised_paper_file = None

    for review in submission.reviews.all():
        if review.commented_paper_file:
            if clear_file_field(review.commented_paper_file, save_instance=False):
                deleted += 1
            review.commented_paper_file = None
            review.save(update_fields=["commented_paper_file", "updated_at"])

    submission.save(update_fields=[
        "anonymized_paper_file",
        "layout_revised_paper_file",
        "updated_at",
    ])

    return deleted
