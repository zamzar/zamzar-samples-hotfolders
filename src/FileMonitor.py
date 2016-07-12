"""
    Written by Joseph Anderson using the Zamzar file conversion API

    A script to monitor folders and subdirectories for file movement, creation
    or modification so that files are automatically converted from predefined
    filetypes to target filetypes set by the user.

    Zamzar API keys can be obtained by registering here: https://developers.zamzar.com/pricing
"""

from watchdog.events import FileSystemEventHandler
import time
import requests
import os
import zipfile
from requests.auth import HTTPBasicAuth


class FileMonitor(FileSystemEventHandler):
    """ This class extends the FileSystemEventHandler class from the Watchdog library. """

    def __init__(self, to_formats, from_formats, option_info, ignore_info, api_key):
        self.to_formats = to_formats
        self.from_formats = from_formats
        self.option_info = option_info
        self.ignore_info = ignore_info
        # This list exists for as long as the class does and holds the paths of failed conversions
        self.ignore_list = list()
        self.api_key = api_key

    # These three methods are called whenever an event of their type is raised, all of them handle the event in the same
    # way, by calling handle_event.
    def on_created(self, event):
        self.handle_event(event)

    def on_modified(self, event):
        self.handle_event(event)

    def on_moved(self, event):
        self.handle_event(event)

    @staticmethod
    def get_file_directory(path):
        """ Convenience method to find the path of the directory a file exists in
        :param path: The full path of a file
        :return: The path of the directory that the file is in
        """

        destination = path.split(os.path.sep)
        del (destination[len(destination) - 1])
        return os.path.sep.join(destination)

    def is_ignored(self, path):
        """ Checks if a file path is in the ignore list specified by the user or the internal ignore list used for
            failed conversions.
        :param path: The path that may or may not exist in the ignore lists.
        :return: True if the path exists in either ignore list, False otherwise
        """

        for line in self.ignore_info:
            if self.get_file_directory(path) + os.path.sep + line == path:
                return True
        # Check that the source_file is not on the ignore list held internally
        for path in self.ignore_list:
            if path == path:
                return True
        return False

    def generate_file_name(self, file_name, source_file):
        """ Generates a file name (as a full path), essentially just adds numbers if the file is a duplicate in the form
            file_name (1) if file_name is taken.
        :param file_name: the name of the file to be downloaded, that we are checking is not a duplicate name
        :param source_file: used so we can get the directory for the new file, to make the full path
        :return: the full path of the file to be downloaded
        """

        file_name_no_number = file_name
        # Check that the file does not already exist in the folder
        count = 1
        # In practice this loop should always terminate
        while True:
            if file_name not in os.listdir(self.get_file_directory(source_file)):
                break
            else:
                file_name = file_name_no_number
                file_name = file_name + '(' + str(count) + ')'
                count += 1

        return self.get_file_directory(source_file) + os.path.sep + file_name

    def delete_file(self, source_file):
        """ Deletes a file, checks for OSError exceptions
        :param source_file: the file to delete
        :return: None
        """
        # If the file has been converted then delete it
        try:
            os.remove(source_file)
        except OSError:
            # It's highly unlikely that this will be used, only if a user changes the permissions on the folder
            # If the file cannot be deleted then we add it to an ignore list to prevent further attempts at
            # converting it as this would use up credits and storage space on the computer.
            self.ignore_list.append(source_file)

    def extract_zip(self, file):
        """ If the user wants automatic extraction then perform the extraction. This only works for zip files.
        :param file: the file to extract
        :return: None
        """
        if self.option_info["autoextractzip"] == 1 and file.endswith(".zip"):
            _zip = zipfile.ZipFile(file, 'r')
            _zip.extractall(self.get_file_directory(file))
            _zip.close()

    def handle_event(self, event):
        """ This method is called whenever an event of the types moved, modified or created are raised.
        :param event: the event that was detected, since this method is called from all of the detection methods in this
        class we don't know what the event will be before it is received.
        :return: None
        """

        print(event)

        #    To avoid trying to convert a program which is not fully
        #    copied/downloaded a time delay (3s) is used.
        time.sleep(3)

        # Get the file name from the event.
        file_name = event.src_path

        # If the file name ends in one of the from_formats then we convert it.
        for extension in self.from_formats:
            if file_name.endswith(extension):
                if self.convert(file_name):
                    # The convert function returns true if the conversion was successful, if it was successful we
                    # delete the original file, otherwise print an error message.
                    self.delete_file(file_name)
                else:
                    print("Conversion unsuccessful for: " + file_name)

    def convert(self, source_file):
        """ Convert a file to the file types passed to the class object.
            These file types were defined in the constructor of the Watch class.
            :param source_file: the path of the file to be converted to the to_formats.
            :return None
        """

        # We don't want to delete the source file if the conversion was not
        # successful so we use a boolean to check that
        success = False

        # Iterate through the target formats, and convert the file to each one of them, if the format is invalid then
        # The response id will not exist and so we can abort the conversion to that file type.
        for target_format in self.to_formats:

            # Check that the source_file is not on the ignore list from the config file
            if self.is_ignored(source_file):
                return

            # Get the file information for the request, if not found then the file must not exist anymore and so
            # conversion fails.
            try:
                file_content = {'source_file': open(source_file, 'rb')}
            except FileNotFoundError:
                print("File not found: aborting")
                return

            print("Attempting to convert: " + source_file + " to format: " + target_format)

            # Build and send the request, response is res.
            data_content = {'target_format': target_format}

            # Endpoint to start a conversion job
            endpoint = "https://api.zamzar.com/v1/jobs"

            res = requests.post(endpoint, data=data_content, files=file_content,
                                auth=HTTPBasicAuth(self.api_key, '')).json()

            # If there is no 'id' element returned then the conversion was invalid so break from the conversion loop for
            # this target format, otherwise save the id.
            if "id" not in res:
                if res['errors']:
                    for error in res['errors']:
                        print("Error code: " + str(error['code']) + "  -  " + error['message'])
                break
            job_id = res['id']

            # The new endpoint to send requests to is the jobs endpoint using our ID
            endpoint = "https://api.zamzar.com/v1/jobs/{}".format(job_id)

            # Conversions are not instant, use a loop to check if the conversion is finished.
            converted = False
            while not converted:
                # Send a request to find out if the conversion is done
                response = requests.get(endpoint, auth=HTTPBasicAuth(self.api_key, '')).json()

                # If it is finished and has been successful
                if response['status'] == "successful":
                    converted = True

                    # Get the information on the incoming file
                    file_info = response['target_files']
                    file_id = file_info[0]['id']
                    file_name = file_info[0]['name']

                    # This function allows us to deal with duplicate file names and to add the path to the filename
                    local_filename = self.generate_file_name(file_name, source_file)

                    # Change the endpoint to download the converted file
                    endpoint = "https://api.zamzar.com/v1/files/{}/content".format(file_id)

                    # Send our request and download the file
                    response = requests.get(endpoint, stream=True, auth=HTTPBasicAuth(self.api_key, ''))

                    try:
                        with open(local_filename, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=1024):
                                if chunk:
                                    f.write(chunk)
                                    f.flush()

                        print(source_file + " successfully converted and downloaded to: " + local_filename)
                        self.extract_zip(local_filename)
                        # This means that at least one of the target formats was successful so we can delete the file
                        success = True
                    except IOError:
                        print("Error")
                # Conversions may fail for whatever reason, so we print an error and make no changes.
                elif response['status'] == "failed":
                    converted = True
                    print("Failed with code: " + str(response['failure']['code']) + "  -  " + response['failure']['message'])
                # Add a delay so that we aren't sending requests as fast as they can be generated
                time.sleep(1)
        return success
