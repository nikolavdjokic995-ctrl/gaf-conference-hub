from django.core.files.storage import FileSystemStorage


class HybridDocumentStorage(FileSystemStorage):
    pass


class R2Storage(FileSystemStorage):
    pass