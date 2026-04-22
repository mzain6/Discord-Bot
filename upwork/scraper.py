from curl_cffi import requests
import json
from datetime import datetime


class UpworkScraper:
    def __init__(self):
        self.cookies = {
            'visitor_id': '154.81.233.241.1758319784113000',
            'x-spec-id': '970d2c5a-9b69-4b34-bd4d-644eaff57978',
            '_vwo_uuid_v2': 'D058420B0985620645CC5530696B85B5C|c0b68ca30840ff098b042304723ac24f',
            '_vwo_uuid': 'D058420B0985620645CC5530696B85B5C',
            'spt': 'a491ed88-1dd2-4654-9cd2-75b65e6ebbdb',
            '__pdst': '91492cb86a154d908d4b8a1b841052bc',
            '__ps_r': '_',
            '__ps_lu': 'https://www.upwork.com/freelance-jobs/large-language-model/?__cf_chl_tk=zgjfoeo4BhUC3C1aIWxyTMq.SB0s1OgpDyVsA2Filik-1758319773-1.0.1.1-IklCI_GXTAHm5KW7MIA60Gna0AwNS79hi5vj_19qwwo',
            '__ps_did': 'pscrb_f6c248af-4df3-42c0-a208-dd6c149a01cc',
            '__ps_fva': '1758319791167',
            '_ga': 'GA1.1.1907517129.1758319791',
            '_tt_enable_cookie': '1',
            '_ttp': '01K5J0DKVQT5Z9VASA2TWCY3EP_.tt.1',
            '_cq_duid': '1.1770581339.DzOpxw3jjRIFy9eQ',
            '_fbp': 'fb.1.1770581342345.74171297251512716',
            'IR_PI': 'a8c501f5-b118-11f0-a4cb-4dd8b28e2ec7%7C1770667742716',
            'recognized': 'dac83679',
            '__gads': 'ID=29d998160b0e6902:T=1770581429:RT=1770581429:S=ALNI_MY2RRoSJoLcT2kuoAjm5QFC6-g47A',
            '__gpi': 'UID=000012f2bf55a1a9:T=1770581429:RT=1770581429:S=ALNI_MZdZNWdsPZJePCUiKbi9tZ4eeHv_A',
            '__eoi': 'ID=9dcbab9d2591b5b5:T=1770581429:RT=1770581429:S=AA-AfjbCDrF1MI2OuMUh1EEm8jo5',
            '__cflb': '02DiuEXPXZVk436fJfSVuuwDqLqkhavJbNTKkecLdRkzF',
            '_twpid': 'tw.1776251338778.401843238154990709',
            '_gcl_au': '1.1.1272662386.1770581339.1360584956.1776251406.1776251406',
            'company_last_accessed': 'd1039661660',
            'DA_dac83679': 'd252999db4f07eeda3cd6fd6b00058a743a4de5b33768fed74aa12bf9ee7c206',
            'umq_cq': '682',
            'OptanonAlertBoxClosed': '2026-04-17T07:40:39.789Z',
            'ftr_ncd': '6',
            'umq': '908',
            'g_state': '{"i_l":0,"i_ll":1776586719745,"i_e":{"enable_itp_optimization":0},"i_et":1776251337816,"i_b":"hMUMnLSj6+6aXd/buxYKjd3NBtCwoCgB2BogueMHR+M"}',
            'up_g_one_tap_closed': 'true',
            'JobDetailsNuxt_vt': 'oauth2v2_int_715c6952e3819f94325eaaf285b0ec52',
            'enabled_ff': '!CI12577UniversalSearch,!CmpLibOn,!Fluid,!MP16400Air3Migration,!SSINavUser,!i18nGA,CI17409DarkModeUI,JPAir3,OTBnrOn,SSINavUserBpa,TONB2256Air3Migration,i18nOn',
            'visitor_gql_token': 'oauth2v2_int_6d273213af38dc81c4c25caaeb98262b',
            'country_code': 'PK',
            'cookie_prefix': '',
            'cookie_domain': '.upwork.com',
            '_vwo_ds': '3%241776251333%3A85.68544791%3A%3A%3A%3A%3A1776660935%3A1776599234%3A7',
            'cf_clearance': 'P1ydiah9Zo.6JOUTyUwsYYsBgYXq0pjU42Hy0YvV92s-1776660936-1.2.1.1-FZ_LFdUBMEdE4dXkGnNm4ZTScHTLPSvZSe1jYt6MHEbgXITT1s4hUOtSv2H68wevKSmJEy_PZ5se3mtxGCrXj45YaP4j1PEfta54BVKNIAtOyKtV5vEPNl.ztpCqR6YBZhfITw_9pF6cFQMRYlq4y2pjC0zVLRBjBrIMYPs99_TVTvnKSxGmXzdry0R2m057k7ro79xemPItCB1.zRzGYz6ToSXWp2Yh4VE1qpJoS49WFNuNhADh3nuL_vM8y5NmaO_UZs.o5pO1F8_RNNr3HT1mI8eKSNk8kcig_jrE45bDBaiCO5EsqXMzYOeI_rJRUGU1ARa2cOI7_7mRvLtTgA',
            '_vis_opt_s': '3%7C',
            '_vis_opt_test_cookie': '1',
            '_upw_ses.5831': '*',
            '_cq_suid': '1.1776660939.F2OrpDYTIy3u4rJQ',
            'IR_gbd': 'upwork.com',
            '__ps_sr': 'https://www.google.com/',
            '__ps_slu': 'https://www.upwork.com/',
            'visitor_topnav_gql_token': 'oauth2v2_int_1b4029daa29bbad9cac167f0bbe08d90',
            'AttachmentsNuxt_vt': 'oauth2v2_int_5b5f0225ed8c5cdd60f70cbcd0a6dfb2',
            '__cf_bm': 'xac0HQ38aMZKsN3pRwUKRTI9vz91CaBRw0yBW03f0lk-1776661136.0443935-1.0.1.1-WYtDLxnhNWR79K9vZh2UGln.qGwt_ZgDlDuaEHyf.BvggiNO0V4nitc_vy9NXhK9iRn7ECrc2Vme2_lv7FIhg2bd1Fdrlp3WHa_hHo0XqmqFAFBGRvS6GGHiNOpMhagt',
            '_cfuvid': 'RQjdEr59efxyMV88QBLlZEEqtdfW9hfSsxkMHFl3.4M-1776661136.3927085-1.0.1.1-Q0ljfDl7wRkZRpDxOfpxYtHwDGdq77IsfKt1XaP0CuM',
            'XSRF-TOKEN': '9ujy9CCs3OWuBLRatEkfMt3q0TY14bHW',
            '_vwo_sn': '409602%3A2%3A%3A%3A%3A%3A43',
            'UniversalSearchNuxt_vt': 'oauth2v2_int_6214404af33ce8fdee65585c84b8a506',
            'AWSALBTG': '15APRJxlpuga9kSv/DZxORgPrvmgvGgoQw+U3Ffg8EqZknoO3saft3zvn/G9y4ylS2tg7v7A3FN+gcTWPgwuVUo9G2NIYZ0MN5Xbo8XKVfRKiuSr6yPadFOD0TnVhM6WvbcW7jhP9uzk0n707S8sqHPitDEFtU9YAnsSC2bZCsMK',
            'AWSALBTGCORS': '15APRJxlpuga9kSv/DZxORgPrvmgvGgoQw+U3Ffg8EqZknoO3saft3zvn/G9y4ylS2tg7v7A3FN+gcTWPgwuVUo9G2NIYZ0MN5Xbo8XKVfRKiuSr6yPadFOD0TnVhM6WvbcW7jhP9uzk0n707S8sqHPitDEFtU9YAnsSC2bZCsMK',
            'OptanonConsent': 'isGpcEnabled=0&datestamp=Mon+Apr+20+2026+10%3A05%3A41+GMT%2B0500+(Pakistan+Standard+Time)&version=202512.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=1691058527108460544&interactionCount=27&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&geolocation=PK%3BPB&AwaitingReconsent=false&isAnonUser=1&identifierType=Cookie+Unique+Id&iType=undefined&crTime=1776411674368',
            '_cq_session': '19.1776660939203.JRJbUUI41ZA4nTIm.1776661542817',
            '_rdt_uuid': '1770581342694.df7f38d9-7174-4eae-8f99-2643ec3e4641',
            '_rdt_em': ':dddcd270b01e0ddaa18c45c7d52d4631718cdaa26c033682cc118bc061e66940,dddcd270b01e0ddaa18c45c7d52d4631718cdaa26c033682cc118bc061e66940,f8cf05ce478145ae30df3791ca53ce6cdc3c47c305b2d9b9a81d71077f3ae92e',
            '_uetsid': '81d10a8038bb11f1afd385043c590dd3',
            '_uetvid': '5d4f068095a511f0ba2bd5a7faa30cda',
            'IR_13634': '1776661543112%7C0%7C1776661543112%7C%7C',
            '_ga_KSM221PNDX': 'GS2.1.s1776660939$o19$g1$t1776661543$j57$l0$h0',
            'forterToken': '2872549f72e54e14a4088a98a085fb26_1776661541192_2092_UDF43-m4_23ck_/yEMJMI+cD0%3D-23-v2',
            'AWSALB': 'A6lidt+f7yevtUwClfpeJXscvANEVDvm9/nDWtA3tsAJzxsOZORYxLwF0xxUW/o/vsBhRv4Uy6NmcBG4N2GeyB2Y47qJ+z+31niERu51UnLXz0Rwg45ZQMJx9kAM',
            'AWSALBCORS': 'A6lidt+f7yevtUwClfpeJXscvANEVDvm9/nDWtA3tsAJzxsOZORYxLwF0xxUW/o/vsBhRv4Uy6NmcBG4N2GeyB2Y47qJ+z+31niERu51UnLXz0Rwg45ZQMJx9kAM',
            'ttcsid_CGCUGEBC77UAPU79F02G': '1776660939594::0BO3AtAdUteLd5m3pmdR.21.1776661731156.1',
            '_upw_id.5831': '7125c074-4ffb-48b7-b460-73d2be51d11e.1758319786.23.1776661731.1776599549.73b29a98-48a1-4a2a-bb44-fdf923a74232.d03b4383-6f35-4818-9cd7-e76f5ca502be.c2b80b23-353e-4cf9-b83d-8f1ac69fa360.1776660937414.135',
            'ttcsid': '1776660939597::sfXLhILfIWK5KLRQ-Uvq.21.1776661731155.0::1.791608.604046::791554.24.154.189::609677.34.0',
        }

        self.headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': 'Bearer oauth2v2_int_6214404af33ce8fdee65585c84b8a506',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'origin': 'https://www.upwork.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://www.upwork.com/nx/search/jobs/?nbs=1',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'vnd-eo-parent-span-id': '550289d0-2aae-4eb2-88f1-7aab6509cd97',
            'vnd-eo-span-id': '6bcb64fa-eb07-4cf1-9e78-53617fd25473',
            'vnd-eo-trace-id': '9ef19d7c4210815b-KHI',
            'vnd-eo-visitorid': '154.81.233.241.1758319784113000',
            'x-upwork-accept-language': 'en-US',
        }

        self.graphql_url = 'https://www.upwork.com/api/graphql/v1'
        self.base_search_url = 'https://www.upwork.com/nx/search/jobs/'

        self.search_query = '''
  query VisitorJobSearch($requestVariables: VisitorJobSearchV1Request!) {
    search {
      universalSearchNuxt {
        visitorJobSearchV1(request: $requestVariables) {
          paging {
            total
            offset
            count
          }
          results {
            id
            title
            description
            relevanceEncoded
            jobTile {
              job {
                id
                ciphertext: cipherText
                jobType
                weeklyRetainerBudget
                hourlyBudgetMax
                hourlyBudgetMin
                hourlyEngagementType
                contractorTier
                sourcingTimestamp
                createTime
                publishTime
                
                hourlyEngagementDuration {
                  rid
                  label
                  weeks
                  mtime
                  ctime
                }
                fixedPriceAmount {
                  isoCurrencyCode
                  amount
                }
                fixedPriceEngagementDuration {
                  id
                  rid
                  label
                  weeks
                  ctime
                  mtime
                }
              }
            }
          }
        }
      }
    }
  }
  '''

    def fetch_jobs_summary(self, offset=0, count=50, keyword=None):
        """Fetches the latest job postings from Upwork, optionally matching a specific keyword."""
        from urllib.parse import quote
        
        params = {
            'alias': 'visitorJobSearch',
        }

        # The referer should reflect the active search if a keyword is provided
        if keyword:
            referer = f"{self.base_search_url}?q={quote(keyword)}&sort=recency"
        else:
            referer = f"{self.base_search_url}?sort=recency"
        
        custom_headers = dict(self.headers)
        custom_headers['referer'] = referer

        # The 'userQuery' parameter inside requestVariables is the source of truth for Upwork's search engine
        request_vars = {
            'sort': 'recency',
            'highlight': False,
            'paging': {
                'offset': offset,
                'count': count,
            },
        }
        
        if keyword:
            request_vars['userQuery'] = keyword

        json_data = {
            'query': self.search_query,
            'variables': {
                'requestVariables': request_vars
            },
        }

        response = requests.post(
            self.graphql_url,
            params=params,
            cookies=self.cookies,
            headers=custom_headers,
            json=json_data,
            impersonate="chrome124"
        )
        
        response.raise_for_status()
        data = response.json()
        
        try:
            return data['data']['search']['universalSearchNuxt']['visitorJobSearchV1']['results']
        except KeyError:
            print("Failed to parse response structure. Check output:")
            print(json.dumps(data, indent=2))
            return []

    def update_credentials(self, new_cookies: dict, auth_token: str = None):
        """
        Hot-swaps cookies and the Authorization header with fresh values.
        Called by AuthManager after each token refresh cycle.
        Thread-safe: dict.update() is atomic in CPython.
        """
        self.cookies.update(new_cookies)
        if auth_token:
            self.headers['authorization'] = f'Bearer {auth_token}'
        print("[SCRAPER] Credentials updated successfully.")

    def fetch_job_full_details(self, job_id):
        """
        Placeholder for fetching full details.
        Since the exact GraphQL query payload for job details isn't fully reversed yet,
        this will return stub data or fallback details for the second pass.
        """
        # In a real scenario with the reverse-engineered query, we would call the endpoint here.
        # Fallback to returning a None or dictionary indicating missing details
        return None
