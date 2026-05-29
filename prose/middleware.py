import json
from contextvars import ContextVar

_abandoned_sgids_by_field = ContextVar("prose_abandoned_sgids_by_field", default=None)


def get_abandoned_sgids_for_field(field_name):
    data = _abandoned_sgids_by_field.get()
    if not data:
        return []
    return data.get(field_name, [])


def _parse_abandoned_sgids_from_request(request):
    if request.method != "POST":
        return {}

    result = {}
    suffix = "_prose_abandoned_sgids"
    for key in request.POST:
        if not key.endswith(suffix):
            continue
        field_name = key[: -len(suffix)]
        raw = request.POST.get(key, "[]")
        try:
            sgids = json.loads(raw)
        except json.JSONDecodeError:
            sgids = []
        if isinstance(sgids, list):
            result[field_name] = [sgid for sgid in sgids if sgid]
    return result


class ProseEditorMiddleware:
    """
  Parse ``<field>_prose_abandoned_sgids`` from POST data so RichTextField sync
  can delete uploads removed in the editor before the first save.
  """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = None
        if request.method == "POST":
            token = _abandoned_sgids_by_field.set(
                _parse_abandoned_sgids_from_request(request)
            )
        try:
            return self.get_response(request)
        finally:
            if token is not None:
                _abandoned_sgids_by_field.reset(token)
