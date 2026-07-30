def safe_id(job_id: str) -> str:
    """Return a filesystem-safe slug for a job_id.

    Replaces every character that is not alphanumeric, ``-``, or ``_``
    with ``_``.  Used by both the crawler and the pipeline to generate
    HTML filenames, so the two sides must stay in sync.
    """
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(job_id))