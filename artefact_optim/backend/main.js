import fs from 'fs';
import { EnkaClient, DetailedGenshinUser, ArtifactSet, percent } from "enka-network-api";
const enka = new EnkaClient();
// process.chdir(__dirname);

const data = fs.readFileSync('./scrapped_data.json', 'utf8');
const DATABASE = JSON.parse(data);
// enka.cachedAssetsManager.activateAutoCacheUpdater({
//     instant: true, // Run the first update check immediately
//     timeout: 60 * 60 * 1000, // 1 hour interval
//     onUpdateStart: async () => {
//         console.log("Updating Genshin Data...");
//     },
//     onUpdateEnd: async () => {
//         enka.cachedAssetsManager.refreshAllData(); // Refresh memory
//         console.log("Updating Completed!");
//     }
// });

function test_percent(name){
    if (name === "cr" || name === "cd" || name === "heal" || name === "er" ){
        return false;
    }
    return true;
}

function convertStatName(statName) {
    statName = statName.toLowerCase();
    switch (statName) {
        case "crit rate":
            return "cr";
        case "crit dmg":
            return "cd";
        case "energy recharge":
            return "er";
        case "healing bonus":
            return "heal";
        case "elemental mastery":
            return "em";
    }
    return statName.split("dmg")[0].trim();
}

function clean_key_value(key,value,percent){
    const clean_name = convertStatName(key);
    let percentstr = "";
    if (test_percent(clean_name)) {
        percentstr = percent ? "%" : "";

    }
    return {[clean_name + percentstr] : Number(value.toFixed(4)) };
}

function getName(character){
    return DATABASE["characters"][character.characterData.name.get("en")] || character.characterData.name.get("en").toLowerCase();
}

function getStats(character){
    const result = {};
    const char = {}
    char["name"] = getName(character);
    char["talent"] = [character.skillLevels[0].level.base, character.skillLevels[1].level.base, character.skillLevels[2].level.base];
    char["cons"] = character.unlockedConstellations.length;
    char["lvl"] = character.level;
    result["char"] = char;
    const weapon = {};
    weapon["lvl"] = character.weapon.level;
    weapon["refine"] = character.weapon.refinementRank;
    weapon["name"] = DATABASE["weapons"][character.weapon.weaponData.name.get("en")] || character.weapon.weaponData.name.get("en");
    result["weapon"] = weapon;
    const sets = {};
    const stats1 = [];
    const stats2 = [];
    for (const artifact of character.artifacts) {
        const setName = DATABASE["artifacts"][artifact.artifactData.set.name.get("en")] || artifact.artifactData.set.name.get("en");
        sets[setName] = (sets[setName] || 0) + 1;
        stats1.push(clean_key_value(artifact.mainstat.fightPropName.get("en"), artifact.mainstat.rawValue, artifact.mainstat.isPercent));
        for (const substat of artifact.substats.total) {
            stats2.push(clean_key_value(substat.fightPropName.get("en"), substat.rawValue, substat.isPercent));
        }
    }
    result["sets"] = Object.fromEntries(Object.entries(sets).filter(([_, value]) => value >= 2));
    result["stats1"] = stats1;
    result["stats2"] = stats2;
    return result;
}


function create_build(stats){
    let res = "";
    const char = stats["char"];
    const weapon = stats["weapon"];
    const sets = stats["sets"];
    const stats1 = stats["stats1"];
    const stats2 = stats["stats2"];
    res += `${char["name"]} char lvl=${char["lvl"]}/90 cons=${char["cons"]} talent=${char["talent"].join(",")};\n`;
    res += `${char["name"]} add weapon="${weapon["name"]}" refine=${weapon["refine"]} lvl=${weapon["lvl"]}/90;\n`;
    for (const [setName, count] of Object.entries(sets)) {
        res += `${char["name"]} add set="${setName}" count=${count};\n`;
    }
    res += `${char["name"]} add stats`;
    let key, value;
    for (const stat of stats1) {
        
        [key, value] = Object.entries(stat)[0];
        res += ` ${key}=${value}`;
    }
    res += `;\n${char["name"]} add stats`;
    for (const stat of stats2) {
        [key, value] = Object.entries(stat)[0];
        res += ` ${key}=${value}`;
    }
    res += ";\n";
    return res;
}


const wantedCharacters = ["skirk", "escoffier" , "furina" , "citlali"]

async function run(uid) {
    /** @type {DetailedGenshinUser} */
    const user = await enka.fetchUser(uid);
    const characters = user.characters;

    if (characters.length === 0) {
        console.log("This user has no detailed characters on the profile.");
        return;
    }
    for (const character of characters) {
        console.log(`Found character: ${getName(character)}`);
    }

    // get artifacts stats and set bonuses from this character.
    for (const character of characters) {
        const name = getName(character).toLowerCase();
        if (!wantedCharacters.includes(name)) continue;
        const stats = getStats(character);
        const build = create_build(stats);
        console.log(`// Build for ${name}`);
        console.log(build);
        console.log();
    }

}

await run(781929764);
await enka.close();