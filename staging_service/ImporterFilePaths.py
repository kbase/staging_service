from collections import defaultdict

full_importer_list = ["app1", "app2", "app3"]


class ImporterFilePaths:
    def __init__(self, request, config):
        self.config = config
        self.request = request

    def get_mappings(self):
        if request.body is blank:
            return full_importer_list
        else:
            return partial_importer_list
