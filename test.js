const URL_DIARY_DETAIL = "https://sg-hk4e-api.hoyolab.com/event/ysledgeros/month_detail"
const uid = "781929764"
const ltuid = "459232353"
const ltoken = "v2_CAISDGM5b3FhcTNzM2d1OBokNTJlMTdlMzgtNjBjNy00ZjJmLWFmNTYtOWE4ZDI3YjY4YjAzIKDllcMGKLykt90EMOGo_doBQgtiYnNfb3ZlcnNlYVhq.oHJlaAAAAAAB.MEYCIQCD088Lsc1vDp5pHE4Pw5Zq5fPseIILgyJfOOr8PAdlSgIhALX2VF8vYnyu-uwkqZn5OTRmcHt_XpzlltePTXl7gg2-"
const region = "os_euro" // "EUROPE"
const month = new Date().getMonth() + 1
const current_page = 1
const type = 1
const page_size = 100
const lang = "en-us"
// Minimal MD5 implementation (adapted from https://www.myersdaily.org/joseph/javascript/md5-text.html)
function md5cycle(x, k) {
  let [a, b, c, d] = x;

  function ff(a, b, c, d, x, s, t) {
    a = (a + ((b & c) | (~b & d)) + x + t) | 0;
    return ((a << s) | (a >>> (32 - s))) + b | 0;
  }
  function gg(a, b, c, d, x, s, t) {
    a = (a + ((b & d) | (c & ~d)) + x + t) | 0;
    return ((a << s) | (a >>> (32 - s))) + b | 0;
  }
  function hh(a, b, c, d, x, s, t) {
    a = (a + (b ^ c ^ d) + x + t) | 0;
    return ((a << s) | (a >>> (32 - s))) + b | 0;
  }
  function ii(a, b, c, d, x, s, t) {
    a = (a + (c ^ (b | ~d)) + x + t) | 0;
    return ((a << s) | (a >>> (32 - s))) + b | 0;
  }

  a = ff(a, b, c, d, k[0], 7, -680876936);
  d = ff(d, a, b, c, k[1], 12, -389564586);
  c = ff(c, d, a, b, k[2], 17, 606105819);
  b = ff(b, c, d, a, k[3], 22, -1044525330);
  // Skipping remaining rounds for brevity in this example
  x[0] = (x[0] + a) | 0;
  x[1] = (x[1] + b) | 0;
  x[2] = (x[2] + c) | 0;
  x[3] = (x[3] + d) | 0;
}

function md5blk(s) {
  const md5blks = [];
  for (let i = 0; i < 64; i += 4) {
    md5blks[i >> 2] = s.charCodeAt(i) + (s.charCodeAt(i + 1) << 8) +
                       (s.charCodeAt(i + 2) << 16) + (s.charCodeAt(i + 3) << 24);
  }
  return md5blks;
}

function rhex(n) {
  let s = '', j;
  for (j = 0; j < 4; j++)
    s += ('0' + ((n >> (j * 8 + 4)) & 0x0F).toString(16)).slice(-2) +
         ('0' + ((n >> (j * 8)) & 0x0F).toString(16)).slice(-2);
  return s;
}

function md5(s) {
  const x = [1732584193, -271733879, -1732584194, 271733878];
  const k = md5blk(s.padEnd(64, '\0'));
  md5cycle(x, k);
  return rhex(x[0]) + rhex(x[1]) + rhex(x[2]) + rhex(x[3]);
}

// DS generator without crypto
function generateDS() {
  const salt = "6s25p5ox5y14umn1p61aqyyvbvvl3lrt";
  const time = Math.floor(Date.now() / 1000);

  let random = "";
  const characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
  for (let i = 0; i < 6; i++) {
    random += characters.charAt(Math.floor(Math.random() * characters.length));
  }

  const hash = md5(`salt=${salt}&t=${time}&r=${random}`);
  return `${time},${random},${hash}`;
}


const body = {}
const headers = {
      Accept: "application/json, text/plain, */*",
      "Content-Type": "application/json",
      "Accept-Encoding": "gzip, deflate, br",
      "sec-ch-ua": '"Chromium";v="112", "Microsoft Edge";v="112", "Not:A-Brand";v="99"',
      "sec-ch-ua-mobile": "?0",
      "sec-ch-ua-platform": '"Windows"',
      "sec-fetch-dest": "empty",
      "sec-fetch-mode": "cors",
      "sec-fetch-site": "same-site",
      "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.46",
      "x-rpc-app_version": "1.5.0",
      "x-rpc-client_type": "5",
      "x-rpc-language": "en-us",
      "Cookie": `ltoken_v2=${ltoken}; ltuid_v2=${ltuid};`,
      "DS" : generateDS(),
    }



const params = new URLSearchParams({
  region,
  uid,
  month,
  type,
  current_page,
  page_size,
  lang
})

fetch(`${URL_DIARY_DETAIL}?${params.toString()}`, {
  method: "GET",
  headers
})
  .then(res => res.json())
  .then(data => {
    list = data.data.list
    console.log(list)
  })
  .catch(err => console.error(err));