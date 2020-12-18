import os
import json

# Collect Environmental Variables
collection_ids_file = os.environ.get('INPUT_COLLECTION_IDS_FILE_NAME')
path_to_files = os.environ.get('GITHUB_WORKSPACE')
avrae_token = os.getenv('INPUT_AVRAE-TOKEN', None)
modified_files = json.loads(os.getenv('INPUT_MODIFIED-FILES', '[]'))

if __name__ == '__main__':
    # Let's exit if we don't have a token.
    if avrae_token is None:
        print('No Avrae Token Found, Exiting!')
        exit(1)
