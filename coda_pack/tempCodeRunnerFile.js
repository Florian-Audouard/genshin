const token =
	"v2_CAISDGM5b3FhcTNzM2d1OBokNTJlMTdlMzgtNjBjNy00ZjJmLWFmNTYtOWE4ZDI3YjY4YjAzIKDllcMGKLykt90EMOGo_doBQgtiYnNfb3ZlcnNlYVhq.oHJlaAAAAAAB.MEYCIQCD088Lsc1vDp5pHE4Pw5Zq5fPseIILgyJfOOr8PAdlSgIhALX2VF8vYnyu-uwkqZn5OTRmcHt_XpzlltePTXl7gg2-";
const uid = "781929764";
const ltuid = "459232353";
getDailyRewards(uid, token, ltuid, 1).then((reward) => {
	console.log("Daily Primogems: " + reward);
});
