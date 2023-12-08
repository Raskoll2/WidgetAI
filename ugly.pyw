def template(input_string, ipromptBool=False, initial_prompt='', promptTemplate=''):
    if promptTemplate == 'llama':
        #Llama
        ini = f'''[INST]<<SYS>>
{initial_prompt}
<</SYS>>
'''
        prompt = f'''
[INST]
{input_string} [/INST]
'''
        
    elif promptTemplate == 'vicuna':
        #Vicuna
        ini = initial_prompt + '\n'
        prompt = f'''
User:
{input_string}

Assistant:

'''
        
    elif promptTemplate == 'zephyr':
        #Zephyr
        ini = f"<|system|>{initial_prompt}</s>"
        prompt = f'''
<|user|>
{input_string}</s>
<|assistant|>
'''

    elif promptTemplate == 'alpaca':
        #Alpaca
        ini = initial_prompt + '\n'

        prompt = f'''
### Instruction:
{input_string}

### Response:
'''

    elif promptTemplate == 'guanaco':
        #Alpaca
        ini = initial_prompt + '\n'

        prompt = f'''
### Human:
{input_string}

### Assistant:
'''

    elif promptTemplate == 'chatml':
        #Alpaca
        ini = f'''<|im_start|>system
{initial_prompt}<|im_end|>'''

        prompt = f'''
<|im_start|>user
{input_string}<|im_end|>
<|im_start|>assistant
'''

    elif promptTemplate == 'openchat':
        ini = 'GPT4 System: {initial_prompt}'
        prompt = f'''
GPT4 User: Hello, how are you?<|end_of_turn|>GPT4 Assistant: I'm doing well thank you.<|end_of_turn|>
GPT4 User: What are you up to?<|end_of_turn|>GPT4 Assistant: Just reading up on programing and philosophy 📚<|end_of_turn|>
GPT4 User: Do you speak spanish?<|end_of_turn|>GPT4 Assistant: Not unless I'm asked to, and I don't respond in orderd lists either unless asked.<|end_of_turn|>
GPT4 User: {input_string}<|end_of_turn|>GPT4 Assistant: '''

        

    elif promptTemplate == 'story':
        prompt = input_string
        
    else:
        ini = f'<SYS>{initial_prompt}</SYS>\n'
        prompt = f'''
User:
{input_string}

Assistant:

'''

        
    if ipromptBool:
        prompt = ini+prompt

    return prompt











    
