from user_profiling_layer import preferences_management_module


def dumps(user_name):
    return preferences_management_module.get_user_prefs(user_name)


def loads(dump):
    preferences_management_module.update_user_prefs(dump)
