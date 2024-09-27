import json
import boto3
import os
import glob
import logging
import whisperx_transcribe
from subprocess import call
from sqs_message_processor import SQSMessageProcessor
from bedrock_handler.summary_bedrock_handler import SummaryBedrockHandler
from bedrock_handler.audit_bedrock_handler import AuditBedrockHandler
from bedrock_handler.general_bedrock_handler import GeneralPromptHandler
from dotenv import load_dotenv
load_dotenv()

class WhisperSQSMessageProcessor(SQSMessageProcessor): 
    def __init__(self, queue_url, max_number_of_messages=20, wait_time_seconds=10):
        super().__init__(queue_url, max_number_of_messages, wait_time_seconds)
        self.s3 = boto3.client('s3',region_name=self.region)
        self.bedrock_runtime = boto3.client(service_name='bedrock-runtime',region_name=self.region)
        self.audio_extensions = ['.wav', '.mp3', '.m4a']
        self.video_extensions = ['.mp4', '.avi', '.mkv', '.mov']
        self.handler = GeneralPromptHandler(region=self.region)
        
    def download_file(self, bucket_name, object_key):
        self.s3.download_file(bucket_name, object_key, f'/tmp/{object_key}')
        self.logger.info("Downloaded file from S3: s3://%s/%s",bucket_name,object_key)

    def convert_to_audio(self, video_file):
        self.logger.info("Converting the video_file %s to audio_file",video_file)
        audio_file = os.path.splitext(video_file)[0] + '.wav'
        call(['ffmpeg','-hwaccel', 'cuda','-i', video_file, '-vn', '-ar', '16000', '-ac', '1', '-f', 'wav', audio_file,'-y'])
        self.logger.info(f"The audio file is : %s",audio_file)
    
    def get_tag_value(self, tags, key):
        value = tags.get(key)
        if value:
            return value
        else:
            return ""

    def convert_to_asr(self,data):
        counter = 1
        result = ""
        content = ""
        for item in data:
            start_time = self.convert_time(item['start'])
            end_time = self.convert_time(item['end'])
            content += f"{counter}\n{start_time} --> {end_time}\n{item['text']}\n\n"
            if counter % 8 == 0:
                self.handler.prompt('asr',content)
                response_body = self.handler.invoke()
                result = result + "\n\n"+ response_body
                # self.logger.info("Batch-%d inference,result is :\n%s",counter,response_body)
                self.logger.info("Batch-%d inference ",counter)
                content = ""
            counter += 1
            # 处理剩余的数据
        if content:
            self.handler.prompt('asr', content)
            response_body = self.handler.invoke()
            result = result + response_body
        self.logger.info("The asr result is :\n%s",result)
        return result

    def convert_time(self,seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

    def llm_inference(self,prompt,content):
        if prompt == "asr":
            result = self.convert_to_asr(content)
            return result
        self.handler.prompt(prompt,content)
        response_body = self.handler.invoke()
        self.logger.info("The inference info is :\n%s",response_body)
        return response_body
    
    def merge_subtitles(self,subtitle,source_video,output_path):
        # 打开一个文件进行写入
        if os.path.exists('/tmp/subtitles.srt'):
            os.remove('/tmp/subtitles.srt')
        with open('/tmp/subtitles.srt', 'w', encoding='utf-8') as file:
            file.write(subtitle)
        subtitle_filter = f"subtitles='/tmp/subtitles.srt':force_style='FontName=Arial,Fontsize=12'"
        self.logger.info("Merge the subtitles.srt into source video")
        call(['ffmpeg','-hwaccel', 'cuda', '-i', source_video, '-vf',subtitle_filter, output_path,'-y'])

    def transcribe(self, audio_file, message_body,message_receipt_handle):
        bucket_name = message_body['bucket']
        object_key = message_body['key']
        self.logger.info(f"Transcribing the audio file : %s",audio_file)
        file_size_mb = os.path.getsize(audio_file) / (1024 * 1024)
        visibility_timeout = int(file_size_mb * 5 * 10)  # 每MB文件10秒
        self.change_message_visibility(message_receipt_handle, visibility_timeout)

        # 执行transcribe操作
        model_size = self.get_tag_value(message_body.get('tags', {}),"model_size")
        if model_size == "":
            model_size = "large"
        self.logger.info("Use the model size:{0}".format(model_size))
        transcription_text = whisperx_transcribe.transcribe(audio_file, model_size)
        self.logger.info("The transcription text:{0}".format(transcription_text))
        # 判断transcription是否为空，如果不为空，则将transcription内容以json文件的形式上传到S3中
        if transcription_text:
            transcription_key = f"transcribe/{os.path.splitext(object_key)[0]}.json"
            self.s3.put_object(Body=json.dumps(transcription_text,ensure_ascii=False), Bucket=bucket_name, Key=transcription_key)
            self.logger.info("Uploaded transcription text to s3://%s/%s",bucket_name,transcription_key)

        if 'llm_handle' in message_body.get('tags', []):
            handle_list = message_body['tags']['llm_handle'].split('/')
            for handle in handle_list:
                self.logger.info("invoke the llm handler %s ",handle)
                response=self.llm_inference(handle,transcription_text)
                file_key=f"{handle}/{os.path.splitext(object_key)[0]}.txt"
                self.s3.put_object(Body=response.encode('utf-8'), Bucket=bucket_name, Key=file_key)
                self.logger.info("Uploaded %s text to s3://%s/%s",handle,bucket_name,file_key)
                # 将字幕文件合成到视频，并上传到S3中
                if handle == "asr":
                    self.merge_subtitles(response,f'/tmp/{object_key}',f'/tmp/asr-{object_key}')
                    if os.path.exists(f'/tmp/asr-{object_key}'):
                        self.s3.upload_file(f'/tmp/asr-{object_key}', bucket_name, f'video/{object_key}')
                        self.logger.info("Uploaded subtitles merged video file to s3://%s/%s",bucket_name,f'video/{object_key}')
                    else:
                        self.logger.info("Merged video file %s not found, pls check ffmpeg log",f'video/{object_key}')
            if os.path.exists(f'/tmp/asr-{object_key}'):
                os.remove(f'/tmp/asr-{object_key}')
                os.remove(f'/tmp/{object_key}')
                os.remove(f'/tmp/{os.path.splitext(object_key)[0]}.wav')

    # 实现抽象方法，处理业务逻辑
    def process_message(self, message):
        #1. get info from the message
        self.logger.info("Handle the message begin ...")
        message_body = json.loads(message['Body'])
        bucket_name = message_body['bucket']
        object_key = message_body['key']
        message_receipt_handle = message['ReceiptHandle']

        #2.download the file from s3
        if os.path.exists(f'/tmp/{object_key}'):
            os.remove(f'/tmp/{object_key}')
        if os.path.exists(f'/tmp/{os.path.splitext(object_key)[0]}.wav'):
            os.remove(f'/tmp/{os.path.splitext(object_key)[0]}.wav')
        self.download_file(bucket_name, object_key)

        #3.检查文件类型和文件大小
        file_extension = os.path.splitext(object_key)[1].lower()
        if file_extension in self.audio_extensions:
            self.transcribe(f'/tmp/{object_key}',message_body,message_receipt_handle)
        elif file_extension in self.video_extensions:
            self.convert_to_audio(f'/tmp/{object_key}')
            self.transcribe(f'/tmp/{os.path.splitext(object_key)[0]}.wav',message_body,message_receipt_handle)
        else:
            self.logger.info("Unsupported file type: %s",file_extension)
if __name__ == '__main__':
    # queue_url = sys.argv[1]
    queue_url = os.environ['SQS_QUEUE_URL']
    processor = WhisperSQSMessageProcessor(queue_url, max_number_of_messages=1, wait_time_seconds=10)
    processor.process()