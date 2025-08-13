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
  "project_id": "aadml-451013",
  "private_key_id": "8a3a8d2abc5b298f9fee028ac3d4126fd4e89e95",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQChISQaxxf9PYfX\ngdfUv0rTEd+eWc5+G6D22geB65a5rLLjnLuKDdcQJ3Us3XUU0CphQeWAg3XUjvHk\nxOC4hvGjQtrfirS2sYwZtS/GChUnyYSjxFOzx0msOYyVoRls4GyxGCAP4vFe6O+N\nueXFUHtGJRpD7uHXFfTNZuhdSat0odG7hSZ4EE5M5Dby6wok+yBe1A40mKvn/YFx\nYMpzMsxwSoMTr07r+Y3QTepVFZUjdqU/cg1j6Op0l9jv3Tk6269V4cWPDoEefhvl\n9Z3YxNGhpFGdLmcbxL8o9quD70E0QHhQL2wDpuzfZABdqLDOEbIbc9aKoEs9G04D\nI8W0uB6jAgMBAAECggEAC3kyKCv51hxt5Hv2E/BSSQRScYmAjeGP6JiKTivzCUaj\nyqDwrN61R3qNg19DlxdQbmANf+nTV8EvbU+/39h0oM4dQZlGhkCqsrvuM5SopSC1\nt9UHhskGi+OYUlgjj7KoyGfETdZvVaxI9WmmQYBjY1qla6Wm4etuiXIJZQlw0q2o\nqSUGiImsyOCVOs7jce9UAygb0xKrmd/MApwtv9h5HtsCXq4T29v2xjHY9hZCmJ8x\nF+k3Tmerq54B2FWGw+WrDDi2bLFhTCE9P2VUrKvn7Lk7VEub5SUeMua6MUa7qxzO\nRIQXlgnKXCWNzGIuYwxYiC/o5qUDaWVPtq8NE196sQKBgQDewBm9wgDSHsA6j5yy\npiryE9GrPPiRGNuxu43LwGQyM2GuOM9wbJxyIHrsDbkTd+d0/sm69ljncsq2XX1R\n9AC7ZnDho8uiirwIuWOTRafNIWYCqYUgeXDK2iWZEkWgoSxihmqlOY0pfnDA3FWz\nL3G1iX3ljUMQsUYZrfH7CBE+EQKBgQC5LlYtYiEDkMQL0A/tdTO7+ZIdM8Lc73Hc\nzoLtLJIKsHqoVewttxDCRrPudrz5mlB7g+ZPipRYY3oaQgD4m6sjyu9MHDRqQGBx\neHQd3F/8QeStIvenHkgQEI68h3v5JXmI6Y3x4XIAxoP+DUxFgWqRFkSsMAueCwDs\neEbnyMxtcwKBgQCMc14Hu0rfMkqM4j6wmnvbtclvintEqgLkl1j6Dy5eRO2jd+i8\nf49JmtdG/gQjlWgY6gpy26AFF+lfgaViRlMr1pT4gVoF/CpB6fsyQipi+lsi9Jaf\nelM3ZMNuOAo1FUsyOIUH9zjd3/7ibEuRNyogiDgcxKxz2wNTb81zNowAsQKBgG7W\nNypuw4fYzB6t5/qe3doy5Kup4YZPov0gdejzdm4Dd0buNrCeE9/UZbnjQ/S50lY7\nekw9i9DjqZ+xxdcHhYWk31nUv+KgqZkBGa8Nyj24SuD+PvC+BS/oWSaqiR90uKuj\n7xvJbmzcZQBYgUBQ17IDfBL7pthviZv/2aC95O3VAoGAT9B9W2gvjPaGwke8Oav6\nsVAMxt8a0zFKGIafOKKyRPdcN4AJY5q1B6a6hIq7qcEaAH/uZX6bGAceRmrvXRlm\nzxcC5ycl7NDR1bJ/XQob4+DcBksLxBKcLl2+A5wgmgyzwSRPJtJiSXwlqqLSfaim\n1b6HCWKos3TBBkpGewhaoOU=\n-----END PRIVATE KEY-----\n",
  "client_email": "developementlevelbot@aadml-451013.iam.gserviceaccount.com",
  "client_id": "106288661307645661005",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/developementlevelbot%40aadml-451013.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
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
        credentials={ "type": "service_account",
  "project_id": "aadml-451013",
  "private_key_id": "f3d6bc84e5a8c7a9418c9853676c15353be0a5b9",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDJDc9emsaXnEWY\n3iPqB9IyFI9EQTzl4bHgH2ut3zemsCe2PVAfxT4TW7oN1lLEKbwUb/7oumN0zXPX\nioYB2MSeqxcBH3VHGqcahsdcLrhUbGppHlPavg6wzlwUUH7CVsvB9Gd4ErHcqApT\nBXjshW5VYAR2VEzW4atDqaSOtFMFR7OenBY7QfVDzgZK5Ko4/5AuLO/ZR2jNkJA/\n/uI09yGBoAL4zUN26VqbcsTzEMzgWrlt1f4hoowKHP8RtZZBj5gh76PkDU9tIPTg\n0SGlnxuYw+kgF9iX/PD889xq6pcHwqRNVXtUIcnkhfDVZP6PvhV57OSCn5SqY51b\nvFoKKsgpAgMBAAECggEAFD0u5xXbEHeDfQo9oMk1RGPT8TnE/NotqwNWtlvOURoS\nAVMmPfB/2XiGH+73iXYvD/qfNUPQD7m/4852w3hUAKn16J/HUUdSU4YGSxYL6bm5\nM4hBRjeUKIG5fLUGsZ8Fp2poQQrWu0DyOx3FqL+c1fzSriu5yXbRo//PiCsIYXNC\ns85yTWJpIszigbS1agXZxwvbqAdrgYZi7PV5trad63nhXG7+jKlXsP03rFnB++D8\nHCpddNwmwpvTDsogwhgNiaJT/7Nltnz3tSlcuVgQtDzwq5c1V3cKr95p8hTdGiHc\nuZyRzpo4kgffCCC32UM94CBgP3SBsVa0GKJKMjTc5QKBgQD5oWcKtzhF4w8NWADQ\nLP3SpxL5p4/ioarITTr7yM9igNN/6/EMzjpyJ6zFOQRAUCeRTcj0Gy5lv4lRwJkY\nQMTuCPrwtMxoH+Du9jotnx7kf9AaWwqkPqUS0uoiGixKAjjikOOt3KfLjoeu/Vnf\n/4h/sbkRAfdro3Ehy3DkHTtbNQKBgQDOLxp6uZu2ry2IXXKCmkp8fIgg0yh9tGKi\njpE8FbTXl3GmG3JJ8EB1P+Lh2s1kZ85YITJVtqYk2HDw4UVU5CvakPF0Y4lLuyfS\nOW/QZ6yiYP8Gjx5gvmmzvEbe6uFkWkwXzfQAx0QqY10LGeTXEU6PUQt8C3fuSKf7\nPrazxQXjpQKBgES6x6APqhKz3WUTIcYvXQMutO6/z8HaOSdE/ERumYrJZXIHCCs6\nbKUZf1wdwqniZ8J95CIxiajB/5DeskgXLSFMn6q+XLkebdPdP09oTB0lg6p9/oQS\nK2jvYT9abW9DBV57/fPUmO5Wo8zuPFyMAo0F5aplHDYqne9sD/z+f2UxAoGAM3qp\nRtkO2tb0LGcAj0FMtbY2GtP9+RzPv7yO4Iye4XFLi+iwaWuV/HBeCnwh6h7M804e\nji4TX4G2+T2VnPN3S5QC5Udw4TqyX5e9pjAsd0J2ikGzmP4R0DGDFGdarT6qXwsq\nEAOwrlCuy3XEoDoO/lOC5Y7Le/AiGOX4ofvgU40CgYAI5009iHRyFhi2D6VYpd16\ndizzqne/Q51N4b8jhCUHvJEYWuhxSwbYoEBH/hnCbpWikx5n1cfsnoAJhoNn18w/\n1HX2IvNCOizGYvHfrrcRwIwgE8yt3zMflbS1QWvegMqixbaC6TjTJK4CHPpAKd7U\nBuIQLjHI2SaXGygojJyPDw==\n-----END PRIVATE KEY-----\n",
  "client_email": "developementlevelbot@aadml-451013.iam.gserviceaccount.com",
  "client_id": "106288661307645661005",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/developementlevelbot%40aadml-451013.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"}
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
                print('inside')
                self.spreadsheet=self.connection.open_by_url(self.spreadsheet_url)
                print(self.spreadsheet)
            except Exception as e:
                print(e)
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
    
    




