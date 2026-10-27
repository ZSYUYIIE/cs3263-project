# Spot-check sheet

The doc requires our parsed prerequisites and exclusions to be checked by hand against
NUSMods **before** any instances are generated (target: 29 Oct). For each row open the link,
compare, then put your initials in **Checked** and ✅ or ❌ in **OK**. For ❌, add a fix to
`data/manual/overrides.json` (or fix the parser) and note it here.

Rows: the doc's 5 courses + BComp CS core, every course with a parser warning, and 8 random courses (seed 3263).

| Course | Prereq (ours) | Blocked if (ours) | Available | Checked | OK | Notes |
|---|---|---|---|---|---|---|
| [CS3263](https://nusmods.com/courses/CS3263) | (CS2109S or CS2109HS) and (CS2040 or CS2040S or CS2040C or CS2040DE or CS2040HS) and (MA2001 or MA1522 or MA1513 or MA1508E or MA1101R) and (EE2012A or EE2012 or ST2131 or MA2116 or MA2116T or ST2334 or MA2216) | CS3243 | yes |  |  |  |
| [CS2109S](https://nusmods.com/courses/CS2109S) | (YSC2229 or CS2040S or CS2040C or CS2040HS or CS2040 or CS2040DE) and ((MA1511 and MA1512) or MA1521 or MA2002 or MA1102R or MA1312 or MA1507 or MA1505) | DMX1401AI or IT3011 or CS3243 or CS3244 or EE2211 or CG3201 or CS2109HS | yes |  |  |  |
| [CS2109HS](https://nusmods.com/courses/CS2109HS) | (CS2040 or CS2040C or CS2040DE or CS2040HS or CS2040S or YSC2229) and ((MA1511 and MA1512) or MA1312 or MA1505 or MA1521 or MA2002 or MA1531) | CG3201 or CS3243 or CS3244 or DMX1401AI or EE2211 or IT3011 or CS2109S | no |  |  |  |
| [CS3244](https://nusmods.com/courses/CS3244) | (CS2040 or CS2040C or CS2040S or CS2040DE or CS2040HS or YSC2229) and (EE2012A or EE2012 or YSC2243 or ST2131 or ST2334 or MA2116 or MA2116T or MA2216) and ((MA1511 and MA1512) or ((MA2001 or MA1522 or MA1508E or MA1311 or MA1513 or MA1101R) and (MA2002 or MA1521 or MA1505 or MA1507 or MA1102R))) | CS3264 or BT4240 or CS2109S or CS2109HS or DMX1401AI or IT3011 or CG3201 or EE3703 or EE4802 | yes |  |  |  |
| [CS4248](https://nusmods.com/courses/CS4248) | (CS2109S or CS2109HS or CS3244 or MA3270 or ST4248) and (EE2012A or EE2012 or ST2131 or MA2216 or MA2116 or MA2116T or ST2334 or YSC2243) and (MA1505 or MA1507 or MA1521 or MA1102R or YSC1216 or MA2002 or (MA1511 and MA1512)) | CS5246 or DSA4213 | yes |  |  |  |
| [CS1231S](https://nusmods.com/courses/CS1231S) | none | MA1100T or MA1100 or CS1231 | yes |  |  |  |
| [CS2030S](https://nusmods.com/courses/CS2030S) | CS1010 or CS1010E or CS1010X or CS1101S or CS1010S or CS1010J or CS1010A or CS1010HS or UTC2851 | CS2030 or CS2030DE or CS2030HS | yes |  |  |  |
| [CS2040S](https://nusmods.com/courses/CS2040S) | (CS1010 or CS1010E or CS1010X or CS1101S or CS1010S or CS1010J or CS1010A or CS1010HS or UTC2851) and (CS1231S or CS1231 or MA1100 or MA1100T) | CS1020 or CS1020E or CS2020 or CS2010 or CS2040C or CS2040 or CS2040DE or CS2040HS | yes |  |  |  |
| [CS2100](https://nusmods.com/courses/CS2100) | YSC1212 or CS1010 or CS1010J or CS1010E or CS1010S or CS1010X or CS1101S or CS1010A or CS1010HS or UTC2851 | CS2100DE or CS2100HS | yes |  |  |  |
| [CS2103T](https://nusmods.com/courses/CS2103T) | (CS2030 or CS2030S or CS2030DE or CS2030HS) and (CS2040 or CS2040S or CS2040C or CS2040DE or CS2040HS) | CS2103 or CS2103DE or CS2113 or CS2113T or IS2101 or ES2002 or ES2007S or ES2007D or CG1413 or EG1413 or ES1601 | yes |  |  |  |
| [CS2106](https://nusmods.com/courses/CS2106) | CS2100 or CS2100DE or CS2100HS or EE2007 or EE2024 or EE2028 | CG2271 or EE4214 | yes |  |  |  |
| [CS3230](https://nusmods.com/courses/CS3230) | (YSC2229 or CS2040S or CS2040 or CS2040C or CS2040DE or CS2040HS) and (CS1231 or CS1231S or MA1100T or MA1100) | none | yes |  |  |  |
| [CS3243](https://nusmods.com/courses/CS3243) | (CS2040 or CS2040C or CS2040S or CS2040DE or CS2040HS or YSC2229) and (CS1231S or CS1231 or MA1100T or MA1100) | CS2109S or CS2109HS or CS3263 | yes |  |  |  |
| [CS2309](https://nusmods.com/courses/CS2309) | (CS1231 or CS1231S or MA1100 or MA1100T) and (((CS2030 or CS2030S or CS2030DE or CS2030HS) and (CS2040 or CS2040S or CS2040HS or CS2040C or CS2040DE)) or CS2113 or CS2113T) | CS2305S | yes |  |  |  |
| [CS4262](https://nusmods.com/courses/CS4262) | (CS2106 or CG2271) and (CS3244 or CS3264 or CG3201) | CS5462 | yes |  |  |  |
| [CS4240](https://nusmods.com/courses/CS4240) | CS3240 | none | yes |  |  |  |
| [CS3242](https://nusmods.com/courses/CS3242) | (PC1201 or PC1221 or PC1221X) and CS3241 and (MA1522 or MA1508E or MA1513 or MA1311 or MA2001 or MA1101R) and (MA1521 or MA2002 or MA1505 or MA1507 or MA1102R or (MA1511 and MA1512)) | CS4342 | yes |  |  |  |
| [CS2040HS](https://nusmods.com/courses/CS2040HS) | CS1101S or UTC2851 or CS1010 or CS1010A or CS1010E or CS1010FC or CS1010HS or CS1010J or CS1010R or CS1010S or CS1010X | CS2040 or CS2040C or CS2040DE or CS2040S | no |  |  |  |
| [CS2100](https://nusmods.com/courses/CS2100) | YSC1212 or CS1010 or CS1010J or CS1010E or CS1010S or CS1010X or CS1101S or CS1010A or CS1010HS or UTC2851 | CS2100DE or CS2100HS | yes |  |  |  |
| [CS2100HS](https://nusmods.com/courses/CS2100HS) | YSC1212 or CS1010 or CS1010J or CS1010E or CS1010S or CS1010X or CS1101S or CS1010A or CS1010HS or UTC2851 | CS2100DE or CS2100 or CG2028 or EE2028 | yes |  |  |  |
| [CS2106](https://nusmods.com/courses/CS2106) | CS2100 or CS2100DE or CS2100HS or EE2007 or EE2024 or EE2028 | CG2271 or EE4214 | yes |  |  |  |
| [CS2309](https://nusmods.com/courses/CS2309) | (CS1231 or CS1231S or MA1100 or MA1100T) and (((CS2030 or CS2030S or CS2030DE or CS2030HS) and (CS2040 or CS2040S or CS2040HS or CS2040C or CS2040DE)) or CS2113 or CS2113T) | CS2305S | yes |  |  |  |
| [CS5446](https://nusmods.com/courses/CS5446) | (EE2012A or EE2012 or ST2132 or ST2334 or ((ST2131 or MA2116 or MA2116T or MA2216) and (ST1131 or ST1232 or DCS2008 or ST1131A))) and (CS3243 or CS3263) | CS4246 | yes |  |  |  |
| [CS5462](https://nusmods.com/courses/CS5462) | (CS2106 or CG2271) and (CS3244 or CS3264 or CG3201) | CS4262 | yes |  |  |  |
| [CS5477](https://nusmods.com/courses/CS5477) | (MA2001 or MA1522 or MA1101R or MA1311 or MA1506 or MA1508E) and (CS2040 or CS2020 or CS2010 or CS2040S or CS2040C) | CS4277 | yes |  |  |  |
| [EE4211](https://nusmods.com/courses/EE4211) | (EE2211 or EE2213) and (EE2012 or ST2334 or CE2407A) | EE4802 or IT3011 | yes |  |  |  |
| [EE4212](https://nusmods.com/courses/EE4212) | MA1508E and (EE3731C or EE4704) | CS4243 or EE5731 | yes |  |  |  |
| [EE4704](https://nusmods.com/courses/EE4704) | EE2023 or CG2023 | CS4243 or EE3206 or EE3206E or TEE3206 or TEE4704 | yes |  |  |  |
| [EE5132](https://nusmods.com/courses/EE5132) | EE4204 or EE4210 | EE5406 or EE5913 or EE5023 or EE5024 or CS4222 | no |  |  |  |
| [EE5310](https://nusmods.com/courses/EE5310) | EE2012 or EE2012A or ST2334 or EE3204 or EE4204 or EE4210 | EE6310 | no |  |  |  |
| [YSC4216](https://nusmods.com/courses/YSC4216) | YSC2232 and YSC2239 | YSC3227 or (ST3248 and ST4248) | no |  |  |  |
| [CS2108](https://nusmods.com/courses/CS2108) | (CS2040 or CS2040S or CS2040C or CS2040DE or CS2040HS) and (MA1522 or MA2001 or MA1513 or MA1311 or MA1508E) | CS3246 | yes |  |  |  |
| [CS2111](https://nusmods.com/courses/CS2111) | CS1010A or CS1010E or CS1010X or CS1101S or CS1010S or UTC2851 or CS1010HS or CS1010J or CS1010 or NM2207 | none | yes |  |  |  |
| [CS3282](https://nusmods.com/courses/CS3282) | CS3281 | none | yes |  |  |  |
| [DBA3701](https://nusmods.com/courses/DBA3701) | DAO2702 or DAO2702X | DSC3214 or IE2110 | yes |  |  |  |
| [EC2303](https://nusmods.com/courses/EC2303) | none | SA4101 or SA4101C or SA4104 or SA4105 or SA4105C or SA4106 or SA4107 or SA4108 or SA4110 or SA4110C or SA4111 or ST1131 or ST1131A or ST1232 or ST2131 or ST2132 or ST2137 or ST2288 or ST2288R or ST2289 or ST2289R or ST2310 or ST2312 or ST2313 or ST2334 or ST3131 or ST3232 or ST3236 or ST3239 or ST3244 or ST3246 or ST3247 or ST3248 or ST3288 or ST3288R or ST3289 or ST3289R or ST3310 or ST3311 or ST3312 or ST3313 or ST4199 or ST4231 or ST4233 or ST4234 or ST4238 or ST4245 or ST4248 or ST4250 or ST4253 or ST4288 or ST4299 or ST4310 or ST4312 or ST4313 or DSC1007 or DSC1007X or BT1101 or MA2116 | yes |  |  |  |
| [GEK1549](https://nusmods.com/courses/GEK1549) | none | none | no |  |  |  |
| [LSM1301](https://nusmods.com/courses/LSM1301) | none | none | yes |  |  |  |
| [RB1101](https://nusmods.com/courses/RB1101) | none | ME1102 | yes |  |  |  |
