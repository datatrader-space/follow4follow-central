import os
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
import datetime as dt
import uuid
import traceback

class Saver(object):
    def __init__(self):
        
        self.scraped_data=[]
        self.user_followers=[]
        self.user_posts=[]
        self.users=[]
        self.post_comments=[]
        self.follow_relations=[]
        self.parent_tweet=[]
        self.feed_tweets=[]
        self.t_lists=[]
        self.service='instagram'
        self.username=''
        self.end_point='user_posts'
        self.post_id='abcd1234'
        self.file_identifier=''
        self.data_blocks=[]
        self.cached_blocks=[]
        self.sectioned_data=None
        self.file_extension='.json'
        self.empty_file=False
        self.overwrite=False
        self.block_address={}
        self.userId='hamza'

        self.drop_duplicates=False
    def create_data_directory(self):
        pth=os.path.join(os.getcwd(),'data')
        if not os.path.exists(pth):
           os.makedirs(pth)
        self.data_directory=pth
        return self
   

    def create_service_directory(self):

        self.service_directory=os.path.join(self.data,self.service)
        if not os.path.exists(self.service_directory):
            os.makedirs(self.service_directory)    
        return self
    def load_resources(self):
        pth=os.path.join(os.getcwd(),'resources')
        block_address=self.block['address'].split('.')
        for module in block_address:
            if len(module.split(','))>1:
                for _ in module.split(','):
                    pth=os.path.join(pth,_)
               
            pth=os.path.join(pth,module)
        if os.path.exists(pth):
            pass
        else:
            os.makedirs(pth)
        self.block_address=pth
    def load_reports(self):
        pth=os.path.join(os.getcwd(),'reports')
        block_address=self.block['address'].split('.')
        for module in block_address:
            pth=os.path.join(pth,module)
        if os.path.exists(pth):
            pass
        else:
            try:
                os.makedirs(pth)
            except Exception as e:
                print(e)
                print('add report here')
            else:
                pass
        self.block_address=pth
    def load_deep_stuff(self):
        self.create_data_directory()
        pth=os.path.join(os.getcwd(),'deep_stuff')
        block_address=self.block['address'].split('.')
        for module in block_address:
            pth=os.path.join(pth,module)
      
            if os.path.exists(pth):
                pass
            else:
                try:
                    os.makedirs(pth)
                except Exception as e:
                    pass
                    #self.create_report_dump({'service':'storage','end_point':'error','data_point':'makedirs_error',
                                        #'traceback':traceback.format_exc(),'datetime':str(dt.datetime.now()),'dir_path':pth
                                        
                                        
                                        #})
                else:
                    pass
                    #self.create_report_dump({'service':'storage_sense','end_point':'local_storage_sense','data_point':'load_deep_stuff',
                                          #   'type':'makedirs_success',
                                      #  'datetime':str(dt.datetime.now()),'dir_path':pth
                                        
                                        
                                       # })
        self.block_address=pth
    def load_screenshots(self):
        pth=os.path.join(os.getcwd(),'media','screenshots')
        self.block_address=pth
        if os.path.exists(pth):
            pass
        else:
            os.makedirs(pth)

    def load_block(self):
        
        self.create_data_directory()
        block_address=self.block['address'].split('.')
        pth=self.data_directory
        if ',' in block_address:
            print(block_address)
        
        for module in block_address:
            pth=os.path.join(pth,module)
        
        if os.path.exists(pth):
            pass
        else:
            os.makedirs(pth)
        self.block_address=pth
    def create_file_identifier(self):
        import uuid
        
        return str(uuid.uuid1())   
    def add_values_to_file(self,load_block=True):
    
        import uuid
        if load_block:
            self.load_block()
        for extension in ['.json']:
            self.file_extension=extension
            self.open_file() 
                   
            self.write_data_block_to_file()    
    def create_file(self):
        if not self.check_if_file_exists():
           open(self.file, 'w').close()
   
    def open_file(self):
        file_name=self.block.get('file_name')
       
        pth=os.path.join(self.block_address,str(file_name)+self.file_extension)
        
        self.file_path=pth
        try:
            if os.path.exists(pth):
                self.empty_file=False
                if self.file_extension=='.csv':
                    self.file = pd.read_csv(pth)
                elif self.file_extension=='.xlsx':
                    self.file=pd.read_excel(pth,engine='openpyxl')
                elif self.file_extension=='.json':
                    self.file=pd.read_json(open(pth,'r'))
                elif self.file_extension=='.html':
                    self.file=open(pth,'r',encoding='utf-8')
                elif self.file_extension=='.txt':
                    self.file=open(pth,'r',encoding='utf-8')
                    
                
            else:
                self.file = pd.DataFrame()
                self.empty_file=True
            self.data_frame=self.file
            return self
        except Exception as e:
            self.file=None
            self.empty_file=True
            
            _={'traceback':traceback.format_exc(),'service':'Storage','type':'error','error':'open_file_error','block_address':self.block_address,'file_path':self.file_path,'service':self.service,'datetime':dt.datetime.now()}
            from services.reports_manager.manager import Manager
            m=Manager()
            m.report_performance(**_)
                                                                                                             
                                                           
            #self.create_output(_)
            
   

    def write_data_block_to_file(self): 
         
        if self.file is None:
            _={'traceback':traceback.format_exc(),'service':'Storage','type':'error','error':'file_not_open_erro','block_address':self.block_address,'file_path':self.file_path,'service':self.service,'datetime':dt.datetime.now()}
            print(_)
            raise ValueError("File is not open.")    
      
        if self.block.get('data'):
            data=self.block['data']
        else:
            data=self.block
        if type(data)==dict:
            data=[data]
        if self.file_extension=='.html':
            pass
        elif self.file_extension=='.txt':
            pass
        else:
            
            if self.overwrite:
                self.file=pd.DataFrame(data)
            else:          
                self.file = pd.concat([self.file, pd.DataFrame(data)], ignore_index=True)
                if self.drop_duplicates:

                    self.file.drop_duplicates(inplace=True)
        if self.file_extension =='.csv':
            self.file.to_csv(self.file_path)
        elif self.file_extension=='.json':
            self.file.to_json(self.file_path,orient='records')
        elif self.file_extension=='.html':
            
            self.file=open(self.file_path,'w',encoding='utf-8')
            self.file.write(data)
            self.file.close()
        elif self.file_extension =='.txt':
            self.file=open(self.file_path,'w',encoding='utf-8')
            self.file.write(data)
            self.file.close()

        else:
            with pd.ExcelWriter(self.file_path, engine='openpyxl', mode='w') as writer:       
              self.file.to_excel(writer, index=False)
    def add_output_block_to_consumed_blocks_for_audience_for_session(self,session_id,audience_id,output_block):
        self.block={'address':'audience.'+str(audience_id)+'.sessions.'+str(session_id)+'.consumed.blocks','file_name':output_block,'data':[]}
        self.load_block()
        self.add_values_to_file(load_block=False)
    def get_consumed_blocks_for_audience_for_session(self,session_id,audience_id):
        self.block={'address':'audience.'+str(audience_id)+'.sessions.'+str(session_id)+'.consumed.blocks'}
        self.load_block()
        resp=[]
        for block in os.listdir(self.block_address):
            resp.append(block.split('.')[0])
        return resp
    def save_audience_outputs(self,id,data):
        self.block={'address':'audience.'+str(id),'file_name':str(uuid.uuid1()),'data':data}
        self.load_block()
        self.add_values_to_file(load_block=True)
    def retrieve_audience_outputs(self,id,exclude_blocks,keys=False):
        self.block={'address':'audience.'+str(id),'file_name':str(uuid.uuid1())}
        self.load_block()
        print(self.block_address)
        if keys:
            outputs={}
        else:
            outputs=[]
        for output in os.listdir(self.block_address):
            if output.split('.')[0] in exclude_blocks:
                continue
            self.block.update({'file_name':output.split('.')[0]})
            self.open_file()
            if not self.data_frame.empty:
                if keys:
                    outputs.update({output.split('.')[0]:self.data_frame.to_dict(orient='records')})
                else:
                    outputs.extend(self.data_frame.to_dict(orient='records'))
        return outputs