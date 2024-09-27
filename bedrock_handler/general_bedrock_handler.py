import json
from bedrock_handler.prompt_templates import get_prompt
from bedrock_handler.bedrock_handler import BedrockHandler

class GeneralPromptHandler(BedrockHandler):
    # anthropic.claude-3-haiku-20240307-v1:0
    # anthropic.claude-3-5-sonnet-20240620-v1:0
    # anthropic.claude-3-sonnet-20240229-v1:0
    def __init__(self, region, model_id="anthropic.claude-3-sonnet-20240229-v1:0", max_tokens=4000):
        super().__init__('us-west-2', model_id, max_tokens)
        print("init general prompt handler..")

    def prompt(self, prompt_template,content):
        # print(f"prompt_template is {prompt_template}")
        prompt = get_prompt(prompt_template,content)
        self.sys_prompt = prompt
        # print(f"sys_prompt  is {self.sys_prompt}")
