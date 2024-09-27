import abc
import boto3
import json

class BedrockHandler(abc.ABC):
    def __init__(self,region,model_id="",max_tokens = 1000):
        self.bedrock_runtime = boto3.client(service_name='bedrock-runtime',region_name=region)
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.sys_prompt = None

    @abc.abstractmethod
    def prompt(self,*args):
        """
        处理消息的抽象方法,需要在子类中实现具体的处理逻辑。
        """
        pass

    def invoke(self):
        system_prompt = self.sys_prompt
        messages = [{"role": "user", "content":"请按照系统提示直接输出内容,切记任何情况下不要提示”这是结果“，”下面是输出“等内容,也不要输出任何单引号或者双引号，下面请直接开始你的输出:"}]
        body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "system": system_prompt,
                "messages": messages
            })
        response = self.bedrock_runtime.invoke_model(body=body, modelId=self.model_id)
        response_body = json.loads(response.get('body').read())
        print('------- tokens usage -------')
        print(response_body['usage'])
        content = response_body['content'][0]['text']
        return content