import boto3
import json

bedrock_runtime = boto3.client(service_name='bedrock-runtime',region_name='us-west-2')
def invoke():
    system_prompt = "输出标签"
    messages = [{"role": "user", "content":"请按照系统提示直接输出内容,切记任何情况下不要提示”这是结果“，”下面是输出“等内容，下面请直接开始你的输出:"}]
    body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "system": system_prompt,
            "messages": messages
        })
    response = bedrock_runtime.invoke_model(body=body, modelId='anthropic.claude-3-5-sonnet-20240620-v1:0')
    response_body = json.loads(response.get('body').read())
    print('------- tokens usage -------')
    print(response_body['usage'])
    content = response_body['content'][0]['text']
    return content
invoke()
