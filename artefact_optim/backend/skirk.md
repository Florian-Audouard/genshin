// Build for skirk
skirk char lvl=90/90 cons=0 talent=6,10,10;
skirk add weapon="azurelight" refine=1 lvl=90/90;
skirk add set="finaleofthedeepgalleries" count=4;
skirk add stats hp=4780 atk=311 atk%=0.466 cryo%=0.466 cd=0.622;
skirk add stats hp%=0.0583 atk%=0.0991 cd=0.1243 cr=0.0933 atk%=0.0583 def=39.35 cr=0.1205 cd=0.0544 cr=0.07 cd=0.202 hp%=0.1399 hp=268.88 cr=0.0661 cd=0.2021 atk%=0.0816 def=32.4 atk=15.56 cr=0.105 def%=0.1312 atk%=0.1399;


// Build for furina
furina char lvl=90/90 cons=0 talent=1,10,10;
furina add weapon="favsword" refine=3 lvl=90/90;
furina add set="tom" count=4;
furina add stats hp=4780 atk=311 er=0.518 hp%=0.466 cd=0.622;
furina add stats cr=0.07 em=32.64 cd=0.2564 hp%=0.0466 er=0.1879 cr=0.0855 def%=0.1312 cd=0.0622 def=43.98 hp=507.88 def%=0.051 cd=0.1943 em=39.63 cd=0.1166 hp=537.75 cr=0.0778 def=53.24 cr=0.0622 hp%=0.1108 atk%=0.0408;


//cheat stats
furina add stats er=0.35;

// Build for escoffier
escoffier char lvl=90/90 cons=0 talent=1,10,9;
escoffier add weapon="deathmatch" refine=1 lvl=90/90;
escoffier add set="goldentroupe" count=4;
escoffier add stats hp=4780 atk=311 er=0.518 atk%=0.466 cd=0.622;
escoffier add stats hp%=0.0583 cd=0.1321 cr=0.105 atk%=0.1457 em=18.65 cr=0.0583 cd=0.2642 er=0.0518 em=23.31 atk%=0.1691 def=37.03 cd=0.1243 cd=0.0777 er=0.2267 hp=418.26 def=18.52 cr=0.0661 atk%=0.1457 er=0.1231 def%=0.051;


// Build for citlali
citlali char lvl=90/90 cons=0 talent=1,9,6;
citlali add weapon="wanderingevenstar" refine=3 lvl=90/90;
citlali add set="scrolloftheheroofcindercity" count=4;
citlali add stats hp=4780 atk=311 em=186.5 em=186.5 em=186.5;
citlali add stats er=0.0648 em=53.62 cd=0.1399 atk=29.18 cr=0.0389 er=0.0583 hp=268.88 em=104.9 def=32.4 er=0.1554 atk%=0.0525 cr=0.0855 atk=36.96 def=37.03 er=0.1554 def%=0.0729 hp%=0.0933 atk=50.58 def%=0.1385 cr=0.0272;


options swap_delay=12 iteration=100;
target lvl=100 resist=0.1 radius=2 pos=0,2.4 hp=999999999 freeze_resist=0;   # Freezable enemy
//target lvl=100 resist=0.1 radius=2 pos=0,2.4 hp=999999999 freeze_resist=1; # Unfreezable enemy, ~4.5k(~3%) DPS loss (compared to MH variant).
energy every interval=480,720 amount=1;

active furina;

for let r=0; r<4; r=r+1 {
  furina skill, dash, burst;
  citlali skill;
  escoffier skill, burst;

    skirk skill,
          attack:2,burst,
          
          attack:5,
          attack:5,
          attack:5,
          charge,
          attack:5;
}

# Combo: 2[N2D] N3W with some variations
# Skipping Furina's and Escoffier's bursts in the first rotation is a DPS gain.

# 4 Rotations
# Furina E >> Escoffier E N1 >> Citlali E N1 >> Skirk Q tE N2D N2CD N3W 2N2D N3W N2D N2CD N3W 2N2D N2 (~16s first rot)
# Furina N1 Q >> Escoffier E N1 Q >> Furina ED N1 >> Citlali E N1 >> Skirk tE 2N2D N2Q 2(2N2D N3W) N2CD N2D N3W N2D (N3 / N2D N2) (~21s rot)

# Worst-Case DPS (MH + unfreezable) is ~145k (~7k(~5%) DPS loss)