import json
import os
import vimeo
import time
from datetime import datetime
import argparse

RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
MAX_RETRIES = 10

CONFIG_FILE = "/usr/local/bigbluebutton/core/scripts/post_publish/config.json"

def get_client(config):

    if 'client_id' not in config or 'client_secret' not in config:
        raise Exception('We could not locate your client id or client secret ' +
                    'in `' + config_file + '`. Please create one, and ' +
                    'reference `config.json.example`.')

    # Instantiate the library with your client id, secret and access token
    # (pulled from dev site)
    client = vimeo.VimeoClient(
        token=config['access_token'],
        key=config['client_id'],
        secret=config['client_secret']
    )

    return client


def upload(client, file_path, name, meeting_id, project_id):
    print('Uploading: %s' % file_path)

    file_name = name + " " + datetime.now().strftime("%d/%m/%Y-%H:%M")

    try:
        # Upload the file and include the video title and description.
        uri = client.upload(file_path, data={
            'name': file_name,
            'description': "Meeting ID: " + meeting_id
        })

        # Get the metadata response from the upload and log out the Vimeo.com url
        video_data = client.get(uri + '?fields=link').json()
        print('"%s" has been uploaded to %s' % (file_name, video_data['link']))

        video_id = uri[uri.rindex('/')+1:]

        # Make an API call to move video to Semblance folder
        FOLDER_ENDPOINT = '/projects/{project_id}/videos/{video_id}'
        put_uri = FOLDER_ENDPOINT.format(video_id=video_id, project_id=project_id)        

        response = client.put(put_uri)
        print(response)

        '''
        client.patch(uri, data={
            'name': 'Vimeo API SDK test edit',
            'description': "This video was edited through the Vimeo API's " +
                        "Python SDK."
        })

        print('The title and description for %s has been edited.' % uri)
        '''

        # Make an API call to see if the video is finished transcoding.
        video_data = client.get(uri + '?fields=transcode.status').json()
        print('The transcode status for %s is: %s' % (
            uri,
            video_data['transcode']['status']
        ))
    except vimeo.exceptions.VideoUploadFailure as e:
        # We may have had an error. We can't resolve it here necessarily, so
        # report it to the user.
        print('Error uploading %s' % file_name)
        print('Server reported: %s' % e.message)

# if status = true file will upload and status = false file uploaded !
def get_status_upload(meetingid):
    status = True
    status_path = "/var/bigbluebutton/recording/status/"
    vimeo_status = "vimeo/"
    base_vimeo_path = status_path+vimeo_status

    if os.path.exists(base_vimeo_path+meetingid+"-vimeo.done"):
        status = False
    return status

def create_status_upload_vimeo(meetingid):
    status_path = "/var/bigbluebutton/recording/status/"
    vimeo_status = "vimeo/"
    base_vimeo_path = status_path+vimeo_status
    if not os.path.exists(base_vimeo_path):
        os.mkdir(base_vimeo_path)

    os.mknod(base_vimeo_path+meetingid+"-vimeo.done")


def delete_videos_after_30_day():
    path = "/var/bigbluebutton/published/presentation/"
    for f in os.listdir(path):
        if os.stat(os.path.join(path,f)).st_mtime < time.time() - 30 * 86400:
            command = "bbb-record --delete " + f
            os.system(command)

#find videos file in folder
def find(path):
    videos = "*.mp4"
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, videos):
                return os.path.join(root, name)

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='Process meeting info.')
    argparser.add_argument("--meetingid", help="Specifies meetingid!")
    argparser.add_argument("--name", help="meeting name")
    args = argparser.parse_args()
    delete_videos_after_30_day()
    try:
        config = json.load(open(CONFIG_FILE))
        project_id = config['project_id']
        client = get_client(config)
        # If video not already published to vimeo, publish it
        print("Successfully loaded client")
        if get_status_upload(args.meetingid):
            try:
                #file_url = find("/var/bigbluebutton/published/presentation/"+args.meetingid)
                file_url = "/var/bigbluebutton/published/presentation/"+args.meetingid+"/"+args.meetingid+".mp4"
                upload(client,file_url, args.name, args.meetingid, project_id)
                create_status_upload_vimeo(args.meetingid)
            except HttpError, e:
                print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
        else:
            print "Meeting %s uploaded to vimeo !" % (args.meetingid)

    except:
        print("Unable to open config file")