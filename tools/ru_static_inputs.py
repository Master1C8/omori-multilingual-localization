"""Current static-test fixtures from the canonical build index, not old constants."""
import json


def current_inputs(root):
    values = json.loads((root/'translation/ru/current-builds.json').read_text())['staticInputs']
    keys = ['combined', 'display', 'fonts', 'editorial', 'fontReproducibility', 'caseReview']
    if set(values) != set(keys):
        raise ValueError('Exact current static input set required')
    result = {key: (root/values[key]).resolve() for key in keys}
    if any(not path.is_relative_to(root) for path in result.values()):
        raise ValueError('Static fixture outside canonical project')
    return result
