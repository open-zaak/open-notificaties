def preprocess_exclude_endpoints(endpoints, **kwargs):
    """
    preprocessing hook that filters out endpoints from OAS

    TODO remove after commonground-api-common starts supporting drf_spectacular
    """
    exclude = "callbacks"
    return [
        (path, path_regex, method, callback)
        for path, path_regex, method, callback in endpoints
        if path.split("/")[-1] != exclude
    ]
