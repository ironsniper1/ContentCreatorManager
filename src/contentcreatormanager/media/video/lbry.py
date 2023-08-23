"""
Created on Feb 24, 2022

@author: tiff
"""
import os.path
import requests
import contentcreatormanager.media.lbry as lbry_media
import time
import shutil

class LBRYVideo(lbry_media.LBRYMedia):
    """
    classdocs
    """  
    def __init__(self, lbry_channel, ID : str = '', tags : list = [],
                 title : str = '',file_hash : str = '', file_name : str = '',
                 name : str = '', thumbnail_url : str = '', bid : float = .0001,
                 address : str = '', description : str = '', permanent_url : str = '', 
                 languages : list = ['en'], request = None, new_video : bool =False,
                 lic : str = '', license_url : str = ''):
        """
        Constructor takes LBRY Platform object as required parameter.
        LBRY Video Object can be constructed with the results of an 
        API call to claim_list just set the request parameter.  All
        details can be manually set on creation.  bid defaults very
        low, language defaults to en
        """
        super().__init__(lbry_channel=lbry_channel,
                                        file_name=file_name,
                                        thumbnail_url=thumbnail_url, 
                                        description=description,
                                        languages=languages,
                                        permanent_url=permanent_url, 
                                        tags=tags, bid=bid, title=title,
                                        name=name, ID=ID, new_media=new_video,
                                        lic=lic,license_url=license_url)
        self.logger = self.settings.LBRY_logger
        if ID != '':
            self.id = ID
        self.logger.info("Initializing Video Object as a LBRY Video Object")
        
        self.address = address
        self.file_hash = file_hash
        
        if request is not None:
            self.update_from_request(request)
        elif not new_video:
            if ID != '':
                self.update_local()
            elif self.name != '':
                try:
                    self.update_local(use_name=True)
                except IndexError:
                    self.logger.error("Could not update with name not found on LBRY")
        
        self.logger.info("LBRY Video Media Object initialized")
    
    def __upload_new_video(self):
        """
        Private Method for uploading a new video to LBRY.  This uses the 
        stream_create api call.  This method will also set the id to the 
        new claim_id from the upload. This method just makes the API call 
        and does nothing to confirm it worked or is complete.
        """
        
        result = self.platform.api_stream_create(name=self.name, bid=self.bid,
                                                 file_path=self.file,
                                                 title=self.title,
                                                 description=self.description,
                                                 channel_id=self.platform.id,
                                                 languages=self.languages,
                                                 tags=self.tags,
                                                 thumbnail_url=self.thumbnail_url,
                                                 lic=self.license,
                                                 license_url=self.license_url)
        
        if 'error' in result:
            self.logger.error(f"The create call returned an error:\n{result['error']['data']['traceback'][3]}")
            return result
        
        self.logger.info(f"Setting claim_id to {result['result']['outputs'][0]['claim_id']}")
        self.id = result['result']['outputs'][0]['claim_id']
        
        self.logger.info("stream_create API call complete without error")
        return result['result']
    
    def set_file_based_on_title(self):
        valid = '`~!@#$%^&+=,-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        file_name = self.title    

        getVals = [val for val in f"{file_name}.mp4" if val in valid]

        result = "".join(getVals)

        self.logger.info(f"returning and setting the following file name: {result}")

        vid_dir = os.path.join(os.getcwd(), 'videos')
        self.file = os.path.join(vid_dir, result)

        return result
    
    def make_thumb(self):
        """
        Method to make a thumbnail file
        """
        if not os.path.join(self.file):
            self.logger.warning("No Video file found downloading to make thumbnail")
            self.download()
            
        return lbry_media.LBRYMedia.make_thumb(self)
    
    def upload_thumbnail(self, update_video : bool = True, use_existing_thumb_if_present : bool = True):
        """
        Method to upload thumbnail to LBRY and set object thumbnail_url
        """
        if os.path.isfile(self.thumbnail) and use_existing_thumb_if_present:
            thumb_file = self.thumbnail
        else:
            thumb_file = os.path.join(os.getcwd(),
                                      self.get_valid_thumbnail_file_name())
        
        if not os.path.isfile(thumb_file):
            self.logger.warning("No Thumbnail file found generating one")
            self.make_thumb()
        
        result = self.platform.api_upload_thumb(file=thumb_file)
        
        self.thumbnail_url = result['data']['serveUrl']
        self.logger.info(f"set thumb url to {self.thumbnail_url}")
        if update_video:
            return self.update_web()
    
    def update_local(self, use_name : bool = False):
        """
        Method to update the local object properties from LBRY.  
        It will do the LBRY lookup with claim_id unless the
        use_name flag is set to True
        """
        response = super().update_local(use_name=use_name)
        self.set_file_based_on_title()
        
        return response
    
    def download(self):
        """
        Method to download Video from LBRY to local machine.
        This will call get to download blobs, file_save to
        make a file from the blobs and then if the file is
        in the wrong location (due to LBRY API weirdness)
        this Method will put it in the right place
        """
        if not self.is_uploaded():
            self.logger.error("Video not on LBRY can not download it")
            return

        get_result = self.platform.api_get(uri=self.permanent_url,
                                           download_directory=self.settings.folder_location,
                                           file_name=os.path.basename(self.file))

        try:
            streaming_url = get_result['result']['streaming_url']
        except KeyError as e:
            if e.args[0] != 'streaming_url':
                raise e
            m="The Video You are trying to download not found on LBRY"
            self.logger.error(m)
            return 'get_error'
        m=f"running a request {streaming_url} to wait for blobs to finish downloading"
        self.logger.info(m)
        requests.get(streaming_url)

        if os.path.isfile(self.file):
            os.remove(self.file)

        file_save_result = self.platform.api_file_save(claim_id=self.id, 
                                                       download_directory=self.settings.folder_location,
                                                       file_name=os.path.basename(self.file))

        actual_file_path = file_save_result['result']['download_path']
        desired_file_path = self.file

        if actual_file_path == desired_file_path:         
            return get_result

        self.logger.info(f"we want {desired_file_path} we got {actual_file_path} copying to desired location and deleting original")

        shutil.copy(actual_file_path, desired_file_path)
        os.remove(actual_file_path)
        os.remove(os.path.join(os.getcwd(), os.path.basename(desired_file_path)))
    
    def upload(self):
        """
        Method to upload the video to LBRY
        """
        if self.is_uploaded():
            m="You already uploaded this Video to LBRY.  Exitting method"
            self.logger.error(m)
            return

        file_name = os.path.basename(self.file)

        if not os.path.isfile(self.file):
            self.logger.error(f"Can not find file: {file_name}")

        self.logger.info("attempting to upload thumbnail")
        self.upload_thumbnail(update_video=False, use_existing_thumb_if_present=True)

        self.logger.info(f"Attempting to upload {file_name}")
        result = self.__upload_new_video()

        if result is None or 'error' in result:
            m="No Upload made not updating any properties of LBRY Video Object"
            self.logger.error(f'{m}\n{result}')
        else:
            finished = False
            m="Sleeping for 1 min before checking for completion of upload"
            while not finished:
                self.logger.info(m)
                time.sleep(60)
                if self.is_uploaded():
                    self.update_local(use_name=True)
                    finished = True
        return result