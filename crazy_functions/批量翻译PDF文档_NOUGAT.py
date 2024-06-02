from toolbox import CatchException, report_exception, get_log_folder, gen_time_str
from toolbox import update_ui, promote_file_to_downloadzone, update_ui_lastest_msg, disable_auto_promotion
from toolbox import write_history_to_file, promote_file_to_downloadzone
from .crazy_utils import request_gpt_model_in_new_thread_with_ui_alive
from .crazy_utils import request_gpt_model_multi_threads_with_very_awesome_ui_and_high_efficiency
from .crazy_utils import read_and_clean_pdf_text
from .pdf_fns.parse_pdf import parse_pdf, get_avail_grobid_url, translate_pdf
from shared_utils.colorful import *
import copy
import os
import math
import logging

def markdown_to_dict(article_content):
    import markdown
    from bs4 import BeautifulSoup
    cur_t = ""
    cur_c = ""
    results = {}
    for line in article_content:
        if line.startswith('#'):
            if cur_t!="":
                if cur_t not in results:
                    results.update({cur_t:cur_c.lstrip('\n')})
                else:
                    # 处理重名的章节
                    results.update({cur_t + " " + gen_time_str():cur_c.lstrip('\n')})
            cur_t = line.rstrip('\n')
            cur_c = ""
        else:
            cur_c += line
    results_final = {}
    for k in list(results.keys()):
        if k.startswith('# '):
            results_final['title'] = k.split('# ')[-1]
            results_final['authors'] = results.pop(k).lstrip('\n')
        if k.startswith('###### Abstract'):
            results_final['abstract'] = results.pop(k).lstrip('\n')

    results_final_sections = []
    for k,v in results.items():
        results_final_sections.append({
            'heading':k.lstrip("# "),
            'text':v if len(v) > 0 else f"The beginning of {k.lstrip('# ')} section."
        })
    results_final['sections'] = results_final_sections
    return results_final




def 解析PDF_基于NOUGAT(file_manifest, project_folder, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt):
    import copy
    import tiktoken
    TOKEN_LIMIT_PER_FRAGMENT = 1024
    generated_conclusion_files = []
    generated_html_files = []
    DST_LANG = "中文"
    from crazy_functions.crazy_utils import nougat_interface
    from crazy_functions.pdf_fns.report_gen_html import construct_html
    nougat_handle = nougat_interface()
    for index, fp in enumerate(file_manifest):
        if fp.endswith('pdf'):
            chatbot.append(["当前进度：", f"正在解析论文，请稍候。（第一次运行时，需要花费较长时间下载NOUGAT参数）"]); yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
            fpp = yield from nougat_handle.NOUGAT_parse_pdf(fp, chatbot, history)
            promote_file_to_downloadzone(fpp, rename_file=os.path.basename(fpp)+'.nougat.mmd', chatbot=chatbot)
        else:
            chatbot.append(["当前论文无需解析：", fp]); yield from update_ui(      chatbot=chatbot, history=history)
            fpp = fp
        with open(fpp, 'r', encoding='utf8') as f:
            article_content = f.readlines()
        article_dict = markdown_to_dict(article_content)
        logging.info(article_dict)
        yield from translate_pdf(article_dict, llm_kwargs, chatbot, fp, generated_conclusion_files, TOKEN_LIMIT_PER_FRAGMENT, DST_LANG)

    chatbot.append(("给出输出文件清单", str(generated_conclusion_files + generated_html_files)))
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面


