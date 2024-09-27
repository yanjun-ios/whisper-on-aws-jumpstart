from dotenv import load_dotenv
from bedrock_handler.summary_bedrock_handler import SummaryBedrockHandler
from bedrock_handler.audit_bedrock_handler import AuditBedrockHandler
from whisper_sqs_message_processor import WhisperSQSMessageProcessor
load_dotenv()


import streamlit as st
import yt_dlp
import subprocess
import os
import re
import whisperx_transcribe
import tempfile
import boto3
from urllib import parse

s3 = boto3.client('s3')
bucket_name = 'whisper-bucket-091063646508'

def list_files(prefix):
    # Initialize S3 client
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    files = [obj['Key'] for obj in response.get('Contents', [])]
    return files

def main():
    st.title("Videos Management")
    if 'transcription' not in st.session_state:
        st.session_state.transcription=""
    if 'btn_disabled' not in st.session_state:
        st.session_state.btn_disabled = True
    tabs = st.tabs(["Video List","Video File Upload"])
    with tabs[0]:
        # List video files
        video_files = list_files('video/')

        # Streamlit UI
        # st.title('Video List')

        # Display video list
        for idx, video_file in enumerate(video_files):
            video_name = video_file.split('/')[-1].split('.')[0]
            video_url = f'https://d28uasq88yts27.cloudfront.net/{video_file}'
            st.subheader(f'{video_name}')
            st.video(video_url)
            st.write(f'**Link:** {video_url}')
            # Fetch corresponding files from other directories
            asr_file = f'asr/{video_name}.txt'
            summary_file = f'summary/{video_name}.txt'
            tag_file = f'tag/{video_name}.txt'

            if summary_file in list_files('summary/'):
                obj = s3.get_object(Bucket=bucket_name, Key=summary_file)
                summary_content = obj['Body'].read().decode('utf-8')
                summary_content.replace('摘要', ' ')
                summary_content.replace('合规风险', '\n**合规风险**')
                st.write(f'**Summary** {summary_content}')

            if tag_file in list_files('tag/'):
                obj = s3.get_object(Bucket=bucket_name, Key=tag_file)
                tag_content = obj['Body'].read().decode('utf-8')
                st.write(f'**Tags:** {tag_content}')

            if idx != len(video_files) - 1:
                st.write('<hr>', unsafe_allow_html=True)
    with tabs[1]:
        video_file = st.file_uploader("Upload Video File", type=["mp3","mp4"])
        language = None
        button_container = st.container()
        btn_video_upload = st.button("Upload", key="btn_video_upload")

        if btn_video_upload:
            progress_text = "Uploading Video file..."
            progress_value = 10
            progress_bar = st.progress(progress_value, text=progress_text)
            # Save the uploaded file to a temporary file
            file_extension = video_file.name.split('.')[-1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp_file:
                tmp_file.write(video_file.getvalue())
                tmp_file_path = tmp_file.name
            tags = {
                'model_size': 'large',
                'llm_handle': 'asr/tag/summary'
            }

            # Upload the file to S3 and add tags in a single call
            try:
                s3.upload_file(
                    tmp_file_path,
                    bucket_name,
                    video_file.name,
                    ExtraArgs={
                        'Tagging': parse.urlencode(tags)
                    }
                )
            except Exception as e:
                print(f"Error uploading file and adding tags: {e}")
                exit(1)
            progress_value = 100
            progress_text = "Processing completed..."
            progress_bar.progress(progress_value, text=progress_text)

            # # Remove the temporary file
            os.unlink(tmp_file_path)
            # st.experimental_rerun()

if __name__ == "__main__":
    main()