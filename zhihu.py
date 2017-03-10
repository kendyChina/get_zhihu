import requests, re, time, os, json
from PIL import Image
import http.cookiejar as cookielib
import logging
logging.basicConfig(level=logging.INFO)
from bs4 import BeautifulSoup

# http头
headers = {
    'Host': 'www.zhihu.com',
    # agent 最重要，请求的身份
    'User-Agent': 'Mozilla / 5.0(Windows NT 10.0;WOW64) AppleWebKit / 537.36(KHTML, likeGecko) Chrome / 50.0.2661.102Safari / 537.36',
    # 防盗链
    'Referer': 'https://www.zhihu.com/'
}
# 在整个爬取过程中，该对象都会保持模拟登陆:
session = requests.session()
session.cookies = cookielib.LWPCookieJar(filename='cookies')
try:
    session.cookies.load(ignore_discard=True)
except:
    print('Cookie 未能加载')

index_url = 'https://www.zhihu.com'
login_url = 'https://www.zhihu.com/login/email'

# 返回xsrf
def get_xsrf():
    index_page = session.get(index_url, headers=headers)
    html = index_page.text
    pattern = r'name="_xsrf" value="(.*?)"'
    _xsrf = re.findall(pattern, html)[0]
    return _xsrf

# 返回captcha
def get_captcha():
    timestamp = str(int(time.time() * 1000))
    captcha_url = 'https://www.zhihu.com/captcha.gif?r=' + timestamp + '&type=login'
    r = session.get(captcha_url, headers=headers)
    with open('captcha.gif', 'wb') as f:
        f.write(r.content)
    try:
        im = Image.open('captcha.gif')
        im.show()
        im.close()
    except:
        print('请到%s目录找到captcha.gif手动输入' % os.path.dirname(__file__))
    captcha = input('请输入验证码\n')
    return captcha

# 判断是否已登录
def is_login():
    is_login_url = 'https://www.zhihu.com/settings/profile'
    sett_page = session.get(is_login_url, headers=headers)
    if sett_page.url == is_login_url:
        return True
    else:
        return False

# 登录
def login():

    if is_login():
        print('已登录。')
        return

    # 登陆数据
    postdata = {
        'email': input('email:\n'),
        'password': input('password:\n'),
        'remember_me': 'true',
        '_xsrf': get_xsrf(),
    }

    try:
        login_page = session.post(login_url, data=postdata, headers=headers)
        logging.info('no captcha.')
    except:
        postdata['captcha'] = get_captcha()
        print(postdata)
        login_page = session.post(login_url, data=postdata, headers=headers)
        logging.info('captcha.')
    session.cookies.save()
    print('登录成功。')

# 获取userID的信息，返回dict
# 传入不需要获取的信息
# name, agree, edit, headline, description, business, locations, educations
def get_userInfo(userID, *args):
    info = {}
    user_url = 'https://www.zhihu.com/people/' + userID
    user_page = session.get(user_url, headers=headers)
    html = user_page.text
    soup = BeautifulSoup(html, 'lxml')
    info['name'] = soup.find_all('span', {'class': 'ProfileHeader-name'})[0].get_text()
    agree_edit = soup.find_all('div', {'class': 'IconGraf'})
    for i in agree_edit:
        text = i.get_text()
        # 赞同
        if '赞同' in text:
            info['agree'] = int(re.findall(r'(\d+)', text)[0])
        # 公共编辑
        else:
            info['edit'] = int(re.findall(r'(\d+)', text)[0])
    # data_state是str类型
    data_state = soup.find_all('div', {'id': 'data'})[0].get('data-state')
    # 用json.loads把<str>转换成<dict>
    data_state = json.loads(data_state)
    # dict
    entities = data_state['entities']
    users = entities['users']
    online_info = users[userID]
    # print(online_info)
    if 'headline' in online_info:
        soup = BeautifulSoup(online_info['headline'], 'lxml')
        headline = soup.find_all('a')
        # 可能为网址或纯文字
        if headline == []:
            info['headline'] = online_info['headline']
        else:
            info['headline'] = headline[0].get_text()
    if 'description' in online_info:
        soup = BeautifulSoup(online_info['description'], 'lxml')
        desc = soup.find_all('a')
        # 可能为网址或纯文字
        if desc == []:
            info['description'] = online_info['description']
        else:
            info['description'] = desc[0].get_text()
    if 'business' in online_info:
        info['business'] = online_info['business']['name']
    # 'locations': [{'name': '广州', 'url': '', ...................}]
    if 'locations' in online_info:
        info['locations'] = []
        for l in online_info['locations']:
            info['locations'].append(l['name'])
    if 'educations' in online_info:
        info['educations'] = []
        educations = online_info['educations']
        for e in educations:
            if 'school' in e:
                school = e['school']
                sch_name = school['name']
            else:
                sch_name = None
            if 'major' in e:
                major = e['major']
                maj_name = major['name']
            else:
                maj_name = None
            info['educations'].append({'school': sch_name, 'major': maj_name})
    for k in args:
        if k in info:
            info.pop(k)
    return info

# 获取answer_id的赞同者，写入 answer_id.txt
def get_voters(answer_id):
    paging = {}
    paging['is_end'] = False
    paging['next'] = 'https://www.zhihu.com/api/v4/answers/' + str(answer_id) + '/voters'

    filename = answer_id + '(voters).txt'

    i = 0
    with open(filename, 'w', encoding='utf-8') as f:
        while paging['is_end'] == False:
            next_url = paging['next']
            pattern = r'(answers/.*?$)'
            param = re.findall(pattern, next_url)[0]
            url = 'https://www.zhihu.com/api/v4/' + param
            logging.info(url)
            # time.sleep(2)
            logging.info('getting...')
            resp = session.get(url, headers=headers)
            text = json.loads(resp.text)
            # is_end, totals, previous, is_start, next
            paging = text['paging']
            # avatar_url_template, name, avatar_url, headline, url_token, user_type, url, ...
            data = text['data']
            for d in data:
                logging.info('writing...')
                # f.write(d['name'] + ' ')
                # try:
                #     voter_url = 'https://www.zhihu.com/people/' + d['url_token']
                #     f.write(voter_url)
                # except:
                #     pass
                # finally:
                #     f.write('\n')
                userID = d['url_token']
                if userID is not None:
                    info = str(get_userInfo(d['url_token']))
                    f.write(str(info))
                f.write('\n')

# 获取userID所关注的人
def get_following(userID):
    url = 'https://www.zhihu.com/people/' + userID + '/following'
    resq = session.get(url, headers=headers)
    text = resq.text
    soup = BeautifulSoup(text, 'lxml')
    aTag = soup.find_all('a', {'class': 'UserLink-link'})[1::2]

    filename = userID + '(following).txt'
    with open(filename, 'w', encoding='utf-8') as f:
        for a in aTag:
            f.write(a.get_text() + ' ')
            f.write(a.get('href'))
            f.write('\n')

# 获取关注userID的人
'''
如果关注userID的人太多，
获取的response有一堆null，暂时无解决办法。
待尝试用浏览器爬虫办法。
'''
def get_followers(userID):
    url = 'https://www.zhihu.com/people/' + userID + '/followers'
    resq = session.get(url, headers=headers)
    text = resq.text

# 获取questionID的所有答案
def get_answers(questionID):
    url = 'https://www.zhihu.com/question/' + str(questionID)
    resp = session.get(url, headers=headers)
    text = resp.text
    soup = BeautifulSoup(text, 'lxml')
    data = soup.find_all('div', {'id': 'data'})[0]
    span = soup.find_all('span', {'class': 'RichText CopyrightRichText-richText'})
    filename = str(questionID) + '(answers).txt'
    with open(filename, 'w', encoding='utf-8') as f:
        for s in span:
            f.write(str(s.get_text()))

if __name__ == '__main__':
    login()
    # get_voters(25341076)
    # info = get_userInfo('xu-le-xuan-kendy')
    # info = get_userInfo('marcovaldong')
    # print(info)
    # get_following('xu-le-xuan-kendy')
    # get_followers('marcovaldong')
    get_answers(24590883)