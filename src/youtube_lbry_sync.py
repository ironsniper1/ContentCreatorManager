#!/usr/bin/env python3
'''
Created on Mar 4, 2022

@author: tiff
'''

import contentcreatormanager.platform.lbry as lbry_plat
import contentcreatormanager.config as config
import contentcreatormanager.media.video.lbry as lbry_vid
import os.path
import contentcreatormanager.platform.youtube as yt_plat
import contentcreatormanager.media.video.youtube as yt_vid

folder = input("Enter Folder Location:")

settings = config.Settings(logging_config_file='logging.ini', folder_location=folder)



channels = lbry_plat.claim_list(claim_type=['channel'])

print(channels['result']['items'][0]['name'])
choices = {}
for count, channel in enumerate(channels['result']['items'], start=1):
    print(f"{count}. {channel['name']}")
    choices[f'{count}'] = channel
choice = input("Pick the channel you want to upload to (Just enter the number next to it above):")

while choice not in choices:
    print(f"You entered {choice} which is not one of the options")
    choice = input("Pick the channel you want to upload to (Just enter the number next to it above):")

channel_claim_id = choices[choice]['claim_id']

lbry = lbry_plat.LBRY(settings=settings, ID=channel_claim_id, init_videos=True)

default_bid = input("Please enter your default bid for uploading to LBRY (Just hit enter for minimum):")

if default_bid != '':
    default_bid = float(default_bid)

youtube = yt_plat.YouTube(settings=settings, init_videos=True)

youtube_not_lbry = []
lbry_not_youtube = []
priv = input("Should private videos be synced(Y/N)?")
unlist = input("Should unlisted videos be synced(Y/N)?")

for yvid in youtube.media_objects:
    in_lbry = any(lvid.title == yvid.title for lvid in lbry.media_objects)
        #settings.Base_logger.info(f"Adding {yvid.title} since it is not on LBRY")
    if yvid.privacy_status == 'private' and ('y' in priv or 'Y' in priv):
        if not in_lbry:
            youtube_not_lbry.append(yvid)
    elif yvid.privacy_status == 'unlisted' and ('y' in unlist or 'Y' in unlist):
        if not in_lbry:
            youtube_not_lbry.append(yvid)
    elif yvid.privacy_status == 'public':
        if not in_lbry:
            youtube_not_lbry.append(yvid)

for lvid in lbry.media_objects:
    in_yt = any(yvid.title == lvid.title for yvid in youtube.media_objects)
    if not in_yt:
        #settings.Base_logger.info(f"Adding {yvid.title} since it is not on LBRY")
        lbry_not_youtube.append(lvid)

youtube_to_dl = [v for v in youtube_not_lbry if not v.is_downloaded()]
lbry_to_dl = [v for v in lbry_not_youtube if not v.is_downloaded()]
for v in lbry_to_dl:
    v.download()

for v in youtube_to_dl:
    v.download()

for count, v in enumerate(youtube_not_lbry):
    lvid = lbry_vid.LBRYVideo(lbry_channel=lbry, name=v.title, tags=v.tags, title=v.title, file_name=os.path.basename(v.file), description=v.description, new_video=True)
    if default_bid != '':
        lvid.bid = default_bid
    lvid.thumbnail_url = v.get_thumb_url()
    lbry.add_media(lvid)
    if count < 2:
        input(f"About to upload {lvid.file} hit Enter to upload")
    lvid.upload()


for v in lbry_not_youtube:
    yvid = yt_vid.YouTubeVideo(channel=youtube, self_declared_made_for_kids=False, made_for_kids=False, public_stats_viewable=True, embeddable=True, privacy_status='unlisted', title=v.title, description=v.description, file_name=os.path.basename(v.file), update_from_web=False, tags=v.tags, new_video=True)
    youtube.add_media(yvid)
    yvid.upload()