"""
Filters related to the enrollment process.

Each filter must follow this naming rule:
...

def {Placement}.{Action}(...):
...

Where Placement can be:
    - after
    - during
    - before

And Action can be:
    - update
    - creation
    - activation
    - deactivation
    - deletion
    ...
"""
from openedx_filters.names import PRE_ENROLLMENT_CREATION
from openedx_filters.pipeline import run_pipeline


def before_creation(user, course_key, *args, **kwargs):
    """
    Filter that executes just before the enrollment is created.

    This filter can alter the enrollment flow, either by modifying the
    incoming user/course or raising an error. It's placed before the
    enrollment is created, so it's garanteed that the user has not
    been enrolled in the course yet.

    Example usage:

    Arguments:
        - user (User): Django User object to be enrolled in the course.
        - course_key (CourseLocator): identifier of the course where the
        user is going to be enrolled (e.g. "edX/Test101/2013_Fall).

    Raises:
    """
    kwargs.update({
        "user": user,
        "course_key": course_key,
    })
    out = run_pipeline(
        PRE_ENROLLMENT_CREATION,
        *args,
        **kwargs
    )
    return out.get("user"), out.get("course_key")
