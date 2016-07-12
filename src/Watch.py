"""
    A script to monitor folders and subdirectories for file movement, creation
    or modification so that files are automatically converted from predefined
    filetypes to target filetypes set by the user.

    Zamzar API keys can be obtained by registering here: https://developers.zamzar.com/pricing
"""

# Imports for polling changes to folders
from watchdog.observers import Observer
from FileMonitor import FileMonitor

class Watch:
    """ A convenience class to make the project slightly neater, just starts and observer thread for a class handling
        the file events, implemented in FileMonitor.py
    """

    def __init__(self, path, to_formats, from_formats, option_info, ignore_info, api_key):
        """ Called upon Watch object creation
            :param path: the file path for the watch
                to_formats: the formats that the path converts to
                from_formats: the formats that the path automatically converts to the to_formats
                option_info: the toggles for the optional functionality
        """
        # It is possible that a user may not have set the recursive search toggle, in which case we default to False.
        if option_info["subdirsearch"]:
            if option_info["subdirsearch"] == 1:
                recursive_toggle = True
            else:
                recursive_toggle = False
        else:
            recursive_toggle = False

        # Make an instance of the FileMonitor class which extends the FileSystemEventHandler class.
        event_handler = FileMonitor(to_formats, from_formats, option_info, ignore_info, api_key)
        # Create the observer thread linked to the FileMonitor instance.
        self.observer = Observer()
        self.observer.schedule(event_handler, path, recursive=recursive_toggle)
        self.observer.start()

    def __del__(self):
        self.observer.stop()
        self.observer.join()
