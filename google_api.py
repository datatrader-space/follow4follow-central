from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import googleapiclient.discovery
from google.oauth2 import service_account
import io
import os

class GoogleAPI(object):
    def __init__(self):
        self.service_name='drive'
        self.media_folder=os.path.join(os.getcwd(),'data','media','media')
        self.credentials_dict={
    "type": "service_account",
    "project_id": "eng-electron-326810",
    "private_key_id": "d1ada37657269a3bae5e65cfec1ceea25c577a86",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCKRJaQr6WofuTb\nULzwLedFOqQqdVhviQW4c7bd1Btxfos1C1ENsYvHYroEmcNSamXk8wkOZcgVm0NC\noBRx9QurfYo20lXyFa4qMxSriBkPAO0iibKQKe5GFk/9+OClYjSu0b+NP3aSvpcX\n1jpOzDEWSDQCJCL3cwo7+R9DoKOQsG0evXAaKC+n4vfj0Ki/BENvx7ZxXfD6zgZC\ncVHDPbimzqE97c2MrGQTjh3vSxMUi6bTeDWzLtxQA6bYUmytx4mgJuEgbtZYVrv3\nLLGL4+GhQfLaBCE33eLmNZxv4T41QypFjc0TmtpZxvPEuFIpj4Jn+TWLPOEHYBOx\nIzlyqn5dAgMBAAECggEAD+Gb56d9IBLfJ3+pC+9B0pZPN989lqYG5a5I0UblFg6i\nX6famfeMJg0lb5TXtfYpmPf/UMuJBU5Nle/8GTC7s+laADz9iS5LUGaIl8Esm6gQ\nFLj7LQrb5un2KyY0a1qR0Yie91LURDum8CJ3lQhoFPabHqnW6FQq10OgfyyKzPoD\neelhSXRnE8jYY/zhnY6/PJ3Jb1csUD+dqdpipRLeilGIj7WGCDm1XcKlobJ/3Bs2\nCMDJ7FRiibYL99xaitqus6Bqj8bBftmNxAhpjGLww5TkCRz5tsc08iPYtUPRPxFT\ns9WYLabdIBh6eizYgdfBxZceO74tml097K7GV0MUgQKBgQDBiyW0njUImjPvp/W5\nz8NJugkHO9As6eKVdhJjknil+8mzDiCbTFi54LHmvanVuMi6sPFCxIIet64BzOAI\nN5yTG1dHVkXtohizfO1eEYc+I8rYDgXMnoqxYLndOGlG8gkrTV5CJALiupwgmctE\nJj1IhD8JMaNDxNiq8FfM9PAQQQKBgQC24w8Lfr/DsNwayovTY8FMCFEoaWEXHisf\n8aAouIPKGq8hdqfYu2mzBmS63RR1gMteZ7TsMdB4n02uOu3QJJLOcjRG4xgmiTaU\nz6vG4Ek/o9a3SZZFGXAtnZpCApWWRh1isb5lQ1JKiUMfHujzU6hZXqe6xBEtSPY7\nx3zP4U7nHQKBgCMDWT7joBR+UQb6C6ohu+KKlTeJyo9VgHgpdAovZUQh2Mtbsupl\nVWfLDmP/y8muNCISAJNjmWaVNBV/Ssgxx1GVkKSHJv9mY7GU2Bw8b4r+TqPnZYUu\n6UhNh1JN8j2za5U52eN9QEhkGfqL2AnsIQoNYpn3MOIBqnDCKiAZ75QBAoGBAJL3\naiqpo36ljGr3I2AvRLFN6bIY5M3ID42vBS5UAIwT33J7wKwZBvq3g5Dqgjte0Y6+\nthQsf8O++JSvhFYEXfkKq1nfupOVJkh1jivWJua+SZimyNwkchImGUU8gGrvU0Px\nY/hKHkIJhefnVfnb22hd+VnLn6YNgNpPF8yR2W89AoGAUJ8NcqHGrRdnw5yPZuVj\nMOYu0LuJIRUAzFkpWGS+1z9rovlu8FCakzZAMgDFdvZrm39VHJjl2fhV9mLOnG/v\nxlSL03q+A1i5sJP54YcYHr8wJAl8ivFQ0LTRomsDXO1F3c0BlcNXqJ1rdSMvhFzY\nsEWmgmFYGrCaQO7iP6Cw97c=\n-----END PRIVATE KEY-----\n",
    "client_email": "testo-1@eng-electron-326810.iam.gserviceaccount.com",
    "client_id": "117026707910158702829",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/testo-1%40eng-electron-326810.iam.gserviceaccount.com"
    }
        self.version='v3'
        if not os.path.isdir(self.media_folder):
            os.makedirs(self.media_folder)
    
    def service_account_from_dict(self):
        credentials = service_account.Credentials.from_service_account_info(self.credentials_dict)
        self.service=googleapiclient.discovery.build(self.service_name,self.version,credentials=credentials)    
    def download_file(self,file):
        file_id=file.get('id',None)
        if not file_id:
            file_id=file.get('url').split('/')[5]
        
        _=self.create_file_path_and_know_export_mime_type(file)
        if 'image' in file['mimeType'] or 'mp4' in file['mimeType']:
            request=self.service.files().get_media(fileId=file_id)
        else:
            request=self.service.files().export_media(fileId=file_id,mimeType=_['export_mime_type'])
        _file = io.BytesIO()
        downloader=MediaIoBaseDownload(_file,request)
        done=False
        while done is False:
            status, done = downloader.next_chunk()
            print(F'Download {int(status.progress() * 100)}.')
        with open(_.get('file_path'),'wb') as file:
            file.write(_file.getvalue())
    def find_file(self,select_first=True,**kwargs):
        file_name=kwargs.get('file_name',None)
        query="name = '"+file_name+"'"
        print(query)
        request=self.service.files().list(q=query).execute()
        
        files=request.get('files',{})
        if len(files)>0:
            if select_first:
                files=[files[0]]       
        else:
            files=[]
        kwargs.update({'files':files})
        return kwargs     
    def find_folder(self,select_first=True,**kwargs,):
        folder_name=kwargs.get('folder_name')
        mimeType = "mimeType = 'application/vnd.google-apps.folder'"
        query="name = '"+folder_name+"' and( "+mimeType+" )"
       
        request=self.service.files().list(q=query).execute()
        
        folders=(request.get('files')) 
        if len(folders)>0:
            if select_first:
                folders=[folders[0]] 
        else:
            folders=[]    
        kwargs.update({'folders':folders})
        return kwargs
    def get_files_in_folder(self,**kwargs):
        resp=self.find_folder(**kwargs)
        if resp.get('folders'):
            folder_id=resp.get('folders')[0]['id']
        request=self.service.files().list(q='"'+folder_id+'" in parents').execute()
        return request.get('files')
    def create_file_path_and_know_export_mime_type(self,file,export_as='',use_file_name=True):
        if file['mimeType']=='image/jpeg':
            _='.jpeg'
            export_mime_type='image/jpeg'
        elif 'mp4' in file['mimeType']:
            _='.mp4'
            export_mime_type='mp4'
        if file['mimeType']=='application/vnd.google-apps.spreadsheet':
            if export_as =='.csv':
                export_mime_type='text/csv'
                _='.csv'
            elif export_as=='.xlsx':
                export_mime_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                _='.xlsx'
            else:
                export_mime_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                _='.xlsx'
        elif file['mimeType']=='application/vnd.google-apps.document':
        
            if export_as=='txt':
                export_mime_type='text/plain'
                _='.txt'
            elif export_as=='.pdf':
                export_mime_type='application/pdf'
                _='.pdf'
            elif export_as=='.docx':
                export_mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                _='.docx'
            else:
                export_mime_type='text/plain'
                _='.txt'
        
        if not use_file_name:
            import uuid
            file_name=str(uuid.uuid1())    
            file_name+=_
        else:
            file_name=file['name']
        
        file_path=os.path.join(self.media_folder,file_name)
        self.download_path=file_path
        return {'file_path':file_path,'export_mime_type':export_mime_type}
    def create_folder(self,name):
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }

        # pylint: disable=maybe-no-member
        file = self.service.files().create(body=file_metadata, fields='id'
                                      ).execute()
        print(F'Folder ID: "{file.get("id")}".')
        return file.get('id')
    def share_with_user(self,**kwargs):
        email_address=kwargs.get('email_address')
        permission_type=kwargs.get('type')
        role=kwargs.get('role')
        file_id=kwargs.get('id')
        body={
                'email_address':kwargs.get('email_address'),
                'type':kwargs.get('type'),
                'role':kwargs.get('role')

        }
        resp=self.service.permissions().create(fileId=file_id,
                                               body=body,
                                               emailMessage='yo hammy',
                                               fields='*').execute()  
    def check_permissions(self,file_id):
        resp=self.service.permissions().list(fileId=file_id,fields='*').execute()
     
        return resp
            

import gspread
import pandas as pd

class GoogleSheet(GoogleAPI):
    def __init__(self):
        self.connection=''
        self.spreadsheet=None
        self.spreadsheet_url=None
        self.worksheet=''
        self.worksheet_title='Profiles'
        self.spreadsheet_title='followers-of-hamza'
        self.active_file=None
        self.folder_name=''
        self.share_with_email_addresses=[]

         
       
    def initialize_connection(self):
        credentials={
            "type": "service_account",
            "project_id": "eng-electron-326810",
            "private_key_id": "d1ada37657269a3bae5e65cfec1ceea25c577a86",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCKRJaQr6WofuTb\nULzwLedFOqQqdVhviQW4c7bd1Btxfos1C1ENsYvHYroEmcNSamXk8wkOZcgVm0NC\noBRx9QurfYo20lXyFa4qMxSriBkPAO0iibKQKe5GFk/9+OClYjSu0b+NP3aSvpcX\n1jpOzDEWSDQCJCL3cwo7+R9DoKOQsG0evXAaKC+n4vfj0Ki/BENvx7ZxXfD6zgZC\ncVHDPbimzqE97c2MrGQTjh3vSxMUi6bTeDWzLtxQA6bYUmytx4mgJuEgbtZYVrv3\nLLGL4+GhQfLaBCE33eLmNZxv4T41QypFjc0TmtpZxvPEuFIpj4Jn+TWLPOEHYBOx\nIzlyqn5dAgMBAAECggEAD+Gb56d9IBLfJ3+pC+9B0pZPN989lqYG5a5I0UblFg6i\nX6famfeMJg0lb5TXtfYpmPf/UMuJBU5Nle/8GTC7s+laADz9iS5LUGaIl8Esm6gQ\nFLj7LQrb5un2KyY0a1qR0Yie91LURDum8CJ3lQhoFPabHqnW6FQq10OgfyyKzPoD\neelhSXRnE8jYY/zhnY6/PJ3Jb1csUD+dqdpipRLeilGIj7WGCDm1XcKlobJ/3Bs2\nCMDJ7FRiibYL99xaitqus6Bqj8bBftmNxAhpjGLww5TkCRz5tsc08iPYtUPRPxFT\ns9WYLabdIBh6eizYgdfBxZceO74tml097K7GV0MUgQKBgQDBiyW0njUImjPvp/W5\nz8NJugkHO9As6eKVdhJjknil+8mzDiCbTFi54LHmvanVuMi6sPFCxIIet64BzOAI\nN5yTG1dHVkXtohizfO1eEYc+I8rYDgXMnoqxYLndOGlG8gkrTV5CJALiupwgmctE\nJj1IhD8JMaNDxNiq8FfM9PAQQQKBgQC24w8Lfr/DsNwayovTY8FMCFEoaWEXHisf\n8aAouIPKGq8hdqfYu2mzBmS63RR1gMteZ7TsMdB4n02uOu3QJJLOcjRG4xgmiTaU\nz6vG4Ek/o9a3SZZFGXAtnZpCApWWRh1isb5lQ1JKiUMfHujzU6hZXqe6xBEtSPY7\nx3zP4U7nHQKBgCMDWT7joBR+UQb6C6ohu+KKlTeJyo9VgHgpdAovZUQh2Mtbsupl\nVWfLDmP/y8muNCISAJNjmWaVNBV/Ssgxx1GVkKSHJv9mY7GU2Bw8b4r+TqPnZYUu\n6UhNh1JN8j2za5U52eN9QEhkGfqL2AnsIQoNYpn3MOIBqnDCKiAZ75QBAoGBAJL3\naiqpo36ljGr3I2AvRLFN6bIY5M3ID42vBS5UAIwT33J7wKwZBvq3g5Dqgjte0Y6+\nthQsf8O++JSvhFYEXfkKq1nfupOVJkh1jivWJua+SZimyNwkchImGUU8gGrvU0Px\nY/hKHkIJhefnVfnb22hd+VnLn6YNgNpPF8yR2W89AoGAUJ8NcqHGrRdnw5yPZuVj\nMOYu0LuJIRUAzFkpWGS+1z9rovlu8FCakzZAMgDFdvZrm39VHJjl2fhV9mLOnG/v\nxlSL03q+A1i5sJP54YcYHr8wJAl8ivFQ0LTRomsDXO1F3c0BlcNXqJ1rdSMvhFzY\nsEWmgmFYGrCaQO7iP6Cw97c=\n-----END PRIVATE KEY-----\n",
            "client_email": "testo-1@eng-electron-326810.iam.gserviceaccount.com",
            "client_id": "117026707910158702829",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/testo-1%40eng-electron-326810.iam.gserviceaccount.com"
            }
        try:     
            self.connection= gspread.service_account_from_dict(credentials)
        except Exception as e:
           print(e)
           pass
        return self
        
    def initialize_google_drive_api(self):
        g=GoogleAPI()
        g.service_account_from_dict()
        self.google_drive_api=g
        return self
    def open_google_sheet(self):
        
        if self.spreadsheet_url:
            import re
            self.spreadsheet_url = re.sub(r'\\\\', r'\\',self.spreadsheet_url)
            try:
                self.spreadsheet=self.connection.open_by_url(self.spreadsheet_url)
            except Exception as e:
                if 'internal error' in str(e):
                    return self.open_google_sheet()
            #print('Opening Google Sheet using URL')
        elif self.active_file:
            if type(self.active_file)==dict:
                #print('Opening Google Sheet using Active File Dict')
                self.spreadsheet=self.connection.open_by_key(self.active_file['id'])
            else:
                #print('Opening Google Sheet using Spreadsheet Object')
                self.spreadsheet=self.connection.open_by_key(self.active_file.id)
        return self
    def create_google_sheet(self):
        self.active_file=self.connection.create(self.spreadsheet_title,self.active_folder['id'])
        print('Created New Google Sheet File')

    def open_worksheet(self):
        sheets=self.spreadsheet.worksheets()  #get all worksheets in the spreadsheet and check if any worksheet exists with user-passed title
        worksheet=None
        self.worksheet=sheets[0]
        return self
    def create_worksheet(self):
        self.worksheet=self.spreadsheet.add_worksheet(self.worksheet_title,rows=1000,cols=30)
        print('Not Found. Created Worksheet')
    def write_to_worksheet(self):
        pass
    def update_worksheet(self,drop_duplicates=True):
        if type(self.data)==list or type(self.data)==dict:
            import pandas as pd
            df=pd.DataFrame.from_records(self.data).fillna(0)
        else:
            df=self.data
        if drop_duplicates:
            df.drop_duplicates(keep='last',inplace=True)
        self.worksheet.update([df.columns.values.tolist()]+ df.values.tolist())
        return self
    def find_worksheet(self,worksheet_title):
        if not self.spreadsheet:
            raise Exception('NoGoogleSheetOpenedException')
        self.worksheet_title=worksheet_title
        #print('Finding Worksheet')
        worksheets=self.spreadsheet.worksheets()
        _=None
        for worksheet in worksheets:
            if worksheet.title.lower()==self.worksheet_title.lower():
                _=worksheet
                #print('Worksheet Found & Turned to Active')
                break
        if _:
            self.worksheet=_
        else:
            self.create_worksheet()
        for worksheet in worksheets:
            if worksheet.title=='Sheet1':
                print('Removed Sheet1')
                self.spreadsheet.del_worksheet(worksheet)
        return self
    def read_worksheet(self):
        print('Reading Active Worksheet')
        try:
            data=self.worksheet.get_all_records()
        except Exception as e:
            print('Empty Sheet')
            self.worksheet_data=[]
        else:
            self.worksheet_data=data
        
        return self
    def check_if_file_exists(self):
        
        resp=self.google_drive_api.find_file(**{'file_name':'branding-sheet'})
        for file in resp['files']:
            if file['mimeType']=='application/vnd.google-apps.spreadsheet':
                self.active_file=file
                return self
        
        return self
    def check_if_folder_exists(self):
        print('Checking if Folder Exists')
        resp=self.google_drive_api.find_folder(**{'folder_name':self.folder_name},select_first=False)
        for folder in resp['folders']:
            self.active_folder=folder
            print('Folder Exists. Turend to Active')
            return self
        print('Folder Not Found.Creating')
        self.active_folder={'id':self.google_drive_api.create_folder(self.folder_name)}
        return self
    def check_if_file_exists_in_active_folder(self):
        print('Checking if file exists in Active Folder')
        files=self.google_drive_api.get_files_in_folder(**{'folder_name':self.folder_name})
      
        if len(files)<1:
            print('Empty Folder.Creating Google Sheet File')
            self.create_google_sheet()
            return self
        else:
            for file in files:
                if file['name']==self.spreadsheet_title and file['mimeType']=='application/vnd.google-apps.spreadsheet':
                    self.active_file=file
                    print('File Exists in Folder. Exiting')
                    return self
        self.create_google_sheet()
        
        return self

    def check_if_file_has_been_shared_with_user(self):
        pass
    def check_if_folder_has_been_shared_with_user(self):
        print('Checking if Folder has been shared with provided email addresses.')
        resp=self.google_drive_api.check_permissions(self.active_folder['id'])
        _emails=self.share_with_email_addresses[:]
        for perm in resp['permissions']:
            for email_address in self.share_with_email_addresses:
                if perm['emailAddress'] in email_address:
                    print('Already Shared with User')
                    _emails.remove(email_address)
                
        
        for email in _emails:
            print('Sharing with '+str(email))
            self.google_drive_api.share_with_user(**{'email_address':email,'role':'writer','type':'user','id':self.active_folder['id']})
           
        return self


        

""" g=GoogleSheet()
g.initialize_google_drive_api()
resp=g.google_drive_api.get_files_in_folder(**{'folder_name':'data-test21'})


g.share_with_email_addresses=['metazon.inc@gmail.com']
g.folder_name='data-test21'
g.initialize_connection().check_if_folder_exists().check_if_folder_has_been_shared_with_user()

g.initialize_connection().check_if_file_exists_in_active_folder().open_google_sheet()
g.worksheet_title='posts'
g.find_worksheet()

g.update_worksheet()
g.worksheet_title='profiles'
g.find_worksheet()
     """





        

    



##files=g.get_files_in_folder(**{'folder_name':'julian_profile_pics'})
#for file in files:
    #g.download_file(file)
    
    




