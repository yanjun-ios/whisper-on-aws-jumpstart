import json

# 总结
summary_prompt = """
# 角色
你是一名出色的文案专家，你擅长审核和总结用户的发言，<transcription_text> 标签中包含的是一段视频的发言稿，你需要仔细阅读并理解发言稿中的内容并进行总结，你总结的内容将作为视频材料的摘要，用于展示和方便用户搜索

# 要求1 - 提取摘要信息
- 识别 <transcription_text> 中的语言种类，用相同语言进行返回摘要信息
- 理解 <transcription_text> 中的主要故事情节,场景,关键词，人物名称等信息，总结成两句话的摘要信息

# 要求1 的示例输出
摘要: 这是一段乔布斯在斯坦福大学的开学典礼上的致辞，他分享了自己三个故事，1.xxx,通过这三个故事来鼓励学生，xxxx

# 要求2 - 审核
您的任务是识别和分类 <transcription_text></transcription_text> 标签中给定发言文稿中的任何不当内容。
您需要按照 <instructions></instructions> 标签中的说明进行操作。

<instructions> 
- 它可能是从视频中提取的语言文字,可能包括同音词、同形异义词或视觉上相似的字符。首先，你需要猜出原始文本是什么。
- 在 <policies></policies>标签中标识提供的政策中的不当内容：注意违规类别可能存在符合"低、中、高"风险等级的情况。
<policies> 
# 账户交易：低：要求账户服务、提及账户交易经验、宣传账户赠品/兑换。中：提供账户交易或账户服务以换取货币。
#诈骗和广告：中：宣传钓鱼网站、免费原始宝石、黑客服务、退款服务或带有购买链接/联系信息的广告。
#信息泄露：低：提及信息泄露事件、黑名单网站。中：讨论或分享泄露的信息。
#言语辱骂和威胁：低：攻击性言论、人身攻击、针对对象的仇恨言论。中：人身攻击、仇恨言论、针对个人/团体的威胁。
#敏感度和裸露：低：提及隐私部位、性行为、要求性服务、与 LGBT（男同性恋、女同性恋等）相关的话题 中：提供或宣传性服务和网站 高：任何针对 LGBT 的歧视
#未成年人安全：低：诱骗行为、将恋童癖正常化、承认与未成年人的恋爱关系。中：涉及未成年人的性内容。高：提供涉及未成年人的性服务、透露账户所有者未满 13 岁。
#非法活动：低：简单提及非法商品/活动、犯罪诱惑、假新闻、阴谋论。
#个人身份信息：低：描述个人信息，如电话号码、地址、身份证、银行账户。
#暴力极端主义：低：提及极端主义、仇恨意识形态，如恐怖主义、白人至上主义、纳粹主义。高：宣传极端主义、仇恨意识形态。
#自杀和自残：低：描述值得信赖的自杀倾向的文本。高：提及或宣传自杀挑战的文本 
</policies>
</instructions>
# 要求2 的示例输出
合规风险:低

以下是上下文:
<transcription_text>
{content}
</transcription_text>

要求输出格式:
摘要: xxx
合规风险:低/中/高

以下是完整的输出示例:
摘要: 这是一段乔布斯在斯坦福大学的开学典礼上的致辞，他分享了自己三个故事，1.xxx,通过这三个故事来鼓励学生，xxxx
合规风险:低

请注意,请严格按照要求输出格式输出内容,不要添加其他任何额外的解释和总结和说明
"""

# ASR
asr_prompt = """
### 任务
你的任务是将<content></content>中的字幕内容翻译成多语言字幕文件，请参考<正向示例></正向示例>中包含的正确的示例，并严格禁止出现<错误示例></错误示例>中的错误格式

### 要求
- <content></content>中的字幕内容是AI从音频中转录获取，可能存在同音错别字的情况，你需要根据上下文的理解猜测并改正成正确的字
- <content></content>中的字幕内容是AI从音频中转录获取可能没有添加断句的标点符合，你需要根据上下文添加逗号，句号，感叹号。
- 如果原始内容是英文字幕，请添加中文，如果原始内容是中文字幕，请添加英文支持，请保持字幕id，时间戳段，中文字幕，英文字幕的顺序。

<正向示例>
### 英文字幕输入内容示例
1
00:00:12,998 --> 00:00:13,398
Thank you.
2
00:00:18,820 --> 00:00:23,662
I'm honored to be with you today for your commencement from one of the finest universities in the world.

### 英文字幕转换后输出示例
1
00:00:12,998 --> 00:00:13,398
谢谢。
Thank you.
2
00:00:18,820 --> 00:00:23,662
我很荣幸今天能在世界上最好的大学之一为你们的毕业典礼致辞。
I'm honored to be with you today for your commencement from one of the finest universities in the world.

### 中字幕输入内容示例
1
00:03:29,868 --> 00:03:36,050
我们把它全都融入到Mac中。那是第一台拥有美丽排版的电脑。

### 中字幕转换后输出示例
1
00:03:29,868 --> 00:03:32,050
我们把它全都融入到Mac中。那是第一台拥有美丽排版的电脑。
And we designed it all into the Mac. It was the first computer with beautiful typography.

</正向示例>

<错误示例>
### 以下是错误的转换格式示例, 这段字幕中，第二句字幕中没有时间段
1
00:01:57,742 --> 00:02:13,116
分享着小区居民理解的眼神与他们热情地打着招呼。
Sharing the understanding gazes of the community residents and greeting them warmly.

每这时候所有的疲惫与委屈对于我们来讲都已经不再重要。
At times like this, all the weariness and grievances no longer matter to us.
</错误示例>

### 以下是正文内容
<content>
{content}
</content>

请注意,对于原始内容，你唯一能修改的是其中可能存在的错别字和添加标点符号，不要修改和添加任何其他内容。你只需要输出转换后的内容，不需要其他任何额外的解释和说明

"""

# 审计
tag_prompt = """
# 角色
你是一个文本分类专家,你的任务是理解<input_content></input_content>中给定的文本,筛选出最合适的几个标签.请注意input_content可能是从视频中提取的语言文字,可能包括同音词、同形异义词或视觉上相似的字符。

# 要求
- 在选择标签的过程中,请保持客观、中立的态度,不带任何个人偏见和主观判断。
- 选择2-6个和内容最相关的标签，如果<tags>中没有合适的标签，你可以根据文章内容自行扩展标签，标签长度不能超过4个字
- 你可以从<input_content></input_content>中识别出现频率较高的词作为标签，如 Python，大数据，生成式AI等
- 输出格式要求不同标签之间用#隔开，不需要任何其他的说明和总结，参考示例输出格式

<tags>
学科教育标签: #语文#数学#英语#物理#化学 等
行业标签: #信息技术#云计算#经济管理#旅游 等
内容标签: #公开演讲#公开课 等
人物标签: #乔布斯#马云#马化腾 等
</tags>

以下是输入的内容:
<input_content>
{content}
</input_content>

示例输出格式:
#AI#公开演讲#乔布斯

"""

# 定义一个字典,将静态字符串映射到对应的键
STRING_MAPPING = {
    "summary": summary_prompt,
    "tag": tag_prompt,
    "asr":asr_prompt
}

def get_prompt(key,content):
    prompt_template = STRING_MAPPING.get(key.lower(), None);
    prompt = prompt_template.replace("{content}",json.dumps(content))
    return prompt