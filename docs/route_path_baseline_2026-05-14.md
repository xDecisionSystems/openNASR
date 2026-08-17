# Route-path baseline classification (2026-05-14)

This note is the tracked evidence for `ROUTE_PATH_PLAN.md` tasks T0.2 and
T0.8. It describes behavior of the production code as it existed on
2026-08-17; it does not redefine a surfaced exception message as the root
cause.

## Method and totals

The 100 rows are the non-empty lines of `tests/exampleRoutes.csv` at the
sorted zero-based indices returned by
`random.Random(20260514).sample(range(46580), 100)`. Joining the sorted
indices as decimal strings with `","` produces SHA-256
`e4a8cbf7b5428f7dc01fc5b89d4264fc2b25e5c85010f3f19ffd2775944773b2`;
joining their route strings with `"\n"` produces SHA-256
`71e060c887646a17681bd8541c8b8f8f0916bfb5cf370290b2aec321e9961750`.
The source file SHA-256 is
`9c52331afa6c8ac5fe661050370bc2fa7ecd87412e241fc55c4f6daf65e6f03c`.

The sample was rerun with CSV storage and the cached archive at
`/home/aev/.cache/openNASR/archives/28DaySubscription_Effective_2026-05-14.zip`.
One `_WaypointResolver` was shared across calls. The result reproduces T0.1:
38 successes and 62 failures.

| Classification | Count | Root-cause rule |
| --- | ---: | --- |
| success | 38 | The current function returned a coordinate tuple. |
| procedure-resolution error | 40 | 39 bare published DPs were lexically dispatched as airways; one dotted DP greedily consumed a following plain fix. |
| airway-resolution error | 7 | A published `Q`/`Y` airway was rejected by the known `AWY_DESIGNATION` comparison bug. |
| waypoint ambiguity | 4 | More than one NASR coordinate survived the current contextual lookup. |
| parser error | 2 | A valid NASR alphanumeric airport/fix (`E91` or `KO60C`) was lexically dispatched as an airway. |
| missing NASR data | 9 | The route requires foreign/oceanic, coordinate, radial-distance, or external route-system content not represented by domestic NASR records. |
| malformed input | 0 | No canonical sample row is malformed. Do not relabel valid unsupported FAA syntax merely to populate this category. |

Classification follows the earliest failure in the current execution. A row
may contain later unsupported content (for example an oceanic continuation)
but remains a procedure error when a preceding bare DP fails first. Bare
procedure classification was verified against `DP_BASE`/`STAR_BASE`, rather
than trusting the misleading surfaced `Airway path` message. Airway cases
were verified to have an `AWY_BASE.AWY_ID` record in this cycle.

## Named fixture routes

These names are stable suggestions for T0.3's curated fixture data:

| Name | Category | Route | Why retained |
| --- | --- | --- | --- |
| `DIRECT_DOMESTIC_CONTROL` | success | `2W5..VKX/0010` | Small successful control. |
| `PARSER_ALPHANUMERIC_AIRPORT` | parser error | `E91..KDVT/0051` | `E91` is a real `APT_BASE.ARPT_ID`, not an airway. |
| `PROCEDURE_BARE_DP_BAYLR6` | procedure-resolution error | `KDEN.BAYLR6.TEHRU..JASSE.Q90.DNERO.ANJLL4.KLAX/0209` | Published bare DP misreported as an airway path. |
| `AIRWAY_Q75_DESIGNATION` | airway-resolution error | `KALB..PWL..BIZEX.Q75.MXE.V378.NUGGY.TRISH4.KBWI/0049` | `Q75` exists in `AWY_BASE`; current designation matching rejects it. |
| `WAYPOINT_ABQ_AMBIGUITY` | waypoint ambiguity | `KABQ..ABQ.V291.GUP..KRQE/0039` | `ABQ` resolves to multiple source coordinates. |
| `UNSUPPORTED_FOREIGN_OCEANIC` | missing NASR data | `CYUL./.RABIK.Q951.ANTOV..EBONY..JEBBY..4300N/05000W..4200N/04000W..4200N/03000W..4200N/02000W..DETOX..LIS..GUDAV..LASIB.M744.SVL..LEMG` | Foreign airports, oceanic coordinates, and non-domestic routing are outside NASR coverage. |
| `MALFORMED_AIRWAY_MISSING_EXIT` | malformed input | `KATL V1` | Synthetic control: the canonical sample has zero malformed rows; this route has a published-airway token without a following endpoint. |

## Canonical 100-row classification

Indices are zero-based positions among the 46,580 non-empty source lines.

| # | Index | Route | Classification | Diagnostic |
| ---: | ---: | --- | --- | --- |
| 1 | 189 | `2W5..VKX/0010` | success | — |
| 2 | 964 | `CYUL./.RABIK.Q951.ANTOV..EBONY..JEBBY..4300N/05000W..4200N/04000W..4200N/03000W..4200N/02000W..DETOX..LIS..GUDAV..LASIB.M744.SVL..LEMG` | missing NASR data | foreign/oceanic |
| 3 | 1729 | `E91..KDVT/0051` | parser error | valid alphanumeric waypoint treated as airway |
| 4 | 1837 | `EGKK./.SNAGY.M203.HOBEE.AR6.HIBAC.DADES2.KTPA` | missing NASR data | foreign |
| 5 | 2271 | `GFS138045..VNY` | missing NASR data | radial-distance point |
| 6 | 2495 | `KABQ..ABQ.V291.GUP..KRQE/0039` | waypoint ambiguity | `ABQ` |
| 7 | 2678 | `KACK..MVY.V146.BAF..MOBBS.T295.SAGES.V489.COATE..KTEB/0059` | waypoint ambiguity | `PVD` while expanding `T295` |
| 8 | 3064 | `KALB..PWL..BIZEX.Q75.MXE.V378.NUGGY.TRISH4.KBWI/0049` | airway-resolution error | published `Q75` rejected |
| 9 | 3370 | `KAPF./.RAPZZ.Q135.RREGG.Q117.SAWED.Q97.ZJAAY.JIIMS4.KTTN/1706` | success | — |
| 10 | 3640 | `KATL.HAALO3.SARGE..DARED..CORKY..KVPS/0048` | procedure-resolution error | bare DP dispatch |
| 11 | 3741 | `KATL.KAJIN2.STNGA..KM18K..ACT..INK..LIFFT.SAMMR3.KELP/0246` | procedure-resolution error | bare DP dispatch |
| 12 | 3896 | `KATL.PADGT2.SMTTH.Q67.HNN..JANYS.ROLLN2.KCLE/0115` | procedure-resolution error | bare DP dispatch |
| 13 | 4134 | `KATL.PHIIL3.PHIIL..CNTLR.JONZE6.KCLT/0040` | success | — |
| 14 | 4475 | `KATL.VARNM2.RESPE..IIU..SPI..STJ..PWE..HCT..OCS..FBR..TCH..BVL..FASTE..LLC..ANAHO.SLMMR5.KSMF/0444` | procedure-resolution error | bare DP dispatch |
| 15 | 4549 | `KATL.VRSTY3.NOKIE..YANTI.Q89.SHRKS..DEBRL.Q97.EBAYY..PBI..ZBV.A555.IDAHO.RTE6.SJU..STT.B520.JUICE..TNCM/0330` | procedure-resolution error | bare DP dispatch |
| 16 | 5144 | `KAZO..SMUUV.WYNDE3.KORD/0029` | success | — |
| 17 | 5158 | `KBAK..ROD..KERI/0049` | success | — |
| 18 | 5337 | `KBDL.THUMB1.CCC..HEADI.Q97.SAWED..MOXXY.Q85.LPERD.SNFLD3.KMCO/0220` | procedure-resolution error | bare DP dispatch |
| 19 | 5407 | `KBED..KHYA` | success | — |
| 20 | 5421 | `KBED..PSM` | success | — |
| 21 | 6797 | `KBOS..LFV..ACK..KACK/0045` | success | — |
| 22 | 6867 | `KBOS./.MEANO.L462.ANVER.MOMOM1.TXKF` | success | — |
| 23 | 7823 | `KBUR.VNY3.FIM..RZS..DINTY..DUETS.R576.DADIE.R576.DIALO.R576.DENNS.MAGGI3.PHNL/0520` | procedure-resolution error | bare DP dispatch |
| 24 | 9474 | `KCLT.ESTRR6.IPTAY..CHOPZ..YAALL..SQS..HAWES..EIC..INK..ELP..CRATT..WOBUG..BXK.J4.WLVRN..ESTWD.HLYWD1.KLAX/0446` | procedure-resolution error | bare DP dispatch |
| 25 | 9617 | `KCLT.JOJJO6.CUBIM.Q50.HELUB..OWB..KOOOP..PIA..COTON..OSH..KATW/0213` | procedure-resolution error | bare DP dispatch |
| 26 | 10006 | `KCMH..POBSE..OHIOS..HVQ.Q147.BURGG..IRQ..WHYYT.GRNCH5.KMCO/0147` | airway-resolution error | published `Q147` rejected |
| 27 | 10018 | `KCMH..POBSE..OHIOS..KTRYN.ONDRE1.KATL/0112` | success | — |
| 28 | 11237 | `KDBQ..KDSM..KDBQ/0243` | success | — |
| 29 | 11786 | `KDEN.BAYLR6.TEHRU..JASSE.Q90.DNERO.ANJLL4.KLAX/0209` | procedure-resolution error | bare DP dispatch |
| 30 | 11829 | `KDEN.BAYLR6.TEHRU..TOADD.Q78.MARUE.JCKIE2.KONT/0203` | procedure-resolution error | bare DP dispatch |
| 31 | 11833 | `KDEN.CHUWY1.CHUWY..ATY..KATY/0102` | success | — |
| 32 | 13898 | `KDTW.KAYLN3.SMUUV..EDENS..LMN..HLC..HGO..LOPEC..TYEGR.CHOWW4.KLAS/2022` | procedure-resolution error | bare DP dispatch |
| 33 | 14154 | `KDVT.DVT3.PXR..3343N/11208W..JONHH.V105.DRK..CRADI..KPRC/0130` | missing NASR data | coordinate point |
| 34 | 14220 | `KDYB..UZA` | success | — |
| 35 | 14321 | `KECP..PZD..PONZE.BANKR6.KCLT/0102` | success | — |
| 36 | 16592 | `KFXE.GABOW2.SUMAC.Y421.HAGIT.Y421.MEEGL..TISX/0221` | procedure-resolution error | bare DP dispatch |
| 37 | 16903 | `KGJT..REMAE..KCEZ/0029` | success | — |
| 38 | 17599 | `KGVL..CANUK..CORKY..KDTS/0121` | success | — |
| 39 | 18390 | `KHPN..LANNA.J48.MOL..FLASK..VIEWS.DEHAN3.KPDK/0139` | success | — |
| 40 | 19034 | `KIAD.JCOBY4.SWANN..BROSS.Q419.RBV..YAHOO..WHALE..NANSO..RAFIN..4500N/05000W..4500N/04000W..4500N/03000W..4530N/02000W..PASAS..VES..LASKU.M190.OBETO.M190.BLV..CEGAM..MALOB..PPN..TURPU..GOSVI..RONKO..RONNY..SURCO..MARIO..POSSY..GRAUS..ALOSU..GEMAS..REBUL..VIBOK..CAVES..BCN..DIPES.N725.OSPOK..NOLVI..ORKUM..ELSAG..ALG..TISAL..ALIXA..ARLOS..SALUN.N705.DEPKA.N705.BOPIX.N710.TAKRI.P751.ALEBA.P751.TOMRU..KSL..ALRAP.T124.AMUDO.AMUDO1A.HAAB/1223` | procedure-resolution error | preceding bare DP dispatch |
| 41 | 19129 | `KIAD.JERES2.JERES.J211.JST..UPPRR.TRYBE4.KCLE/0046` | procedure-resolution error | greedy procedure/fix merge changes airway join |
| 42 | 19503 | `KIAH.GUMBY3.LLA..LEV.Y290.DOWRY.FROGZ5.KMIA/0205` | procedure-resolution error | bare DP dispatch |
| 43 | 20045 | `KIDA.FAHLZ1.SHAEL..PIH.SKEES6.KSLC/0053` | procedure-resolution error | bare DP dispatch |
| 44 | 20385 | `KIND.OOM5.OOM..FAM..WHOLL.BRBBQ3.KMEM/0111` | success | — |
| 45 | 20587 | `KISP..EWB` | success | — |
| 46 | 21402 | `KJFK..SHIPP.Y492.SQUAD..DARUX.L456.NOSID.L457.ENAPI..SHEIL.L459.NUBUS.L459.ODUCA..ELOPO.UB520.ANU.UA632.BGI..TBPB/0431` | airway-resolution error | published `Y492` rejected first |
| 47 | 21730 | `KJQF.ICONS6.NOOKS..WURFL.Q83.JEVED.Q97.PRMUS..JOEYY..DDANY..VALKA..KSUA/0114` | procedure-resolution error | bare DP dispatch |
| 48 | 22025 | `KLAS.GIDGT4.TUKRR..DVC..ALS..TBE..TOTOE..MMB..OKM..HILTY..FAM..WWODD.HANBL3.KDTW/0342` | procedure-resolution error | bare DP dispatch |
| 49 | 22693 | `KLAX.DOTSS2.CLEEE..PKE.J74.TXO.J72.TURKI.JOVEM6.KDFW/0235` | procedure-resolution error | bare DP dispatch |
| 50 | 22944 | `KLAX.ORCKA5.LAS..BAWER.Q114.BUGGG..KD57U..AKO..KD63A..OVR..DSM..EVOTE..NELLS..KEEHO.J584.SLT.FQM3.KEWR/0442` | procedure-resolution error | bare DP dispatch |
| 51 | 23289 | `KLAX.SUMMR2.SCTRR..TROXX.SILCN6.KSJC/0051` | procedure-resolution error | bare DP dispatch |
| 52 | 23667 | `KLGA..BIGGY.Q75.TEUFL..BAAMF.DADES2.KTPA/0337` | airway-resolution error | published `Q75` rejected |
| 53 | 24133 | `KLGB.FRITR3.CNERY..BLH.J169.TFD.J50.SSO.J4.INK..BGTOE.DRYYE2.KDAL/0233` | procedure-resolution error | bare DP dispatch |
| 54 | 24891 | `KMCI.RACER8.BUM..LIT..LEV.L214.IRDOV.UL214.NUDIS.UT38.LEVAT..ITLOM..VOMAR..MMUN/0252` | procedure-resolution error | bare DP dispatch |
| 55 | 25943 | `KMEM.BINKY6.BASBE..KAMEN..DAS..CRP..CAMUI..ITPIS.ITPIS1A.MMMY/0201` | procedure-resolution error | bare DP dispatch |
| 56 | 26231 | `KMFR..CEC` | success | — |
| 57 | 26317 | `KMGR..KIMM/0101` | success | — |
| 58 | 27110 | `KMKC..KFOE..KMKC/0103` | success | — |
| 59 | 27213 | `KMKE..KTOL/0110` | success | — |
| 60 | 28546 | `KMTV..KBKW/0030` | success | — |
| 61 | 28976 | `KOAK.HUSSH2.MOGEE.Q124.BVL.J154.TCH..KAMPR.LONGZ4.KDEN/0206` | procedure-resolution error | bare DP dispatch |
| 62 | 29272 | `KOLV./.MKL245013..M01` | success | — |
| 63 | 29370 | `KOMA..OVR..IRK.J45.STL.J45.LAJUG..HITMN..NEWBB..IHAVE..MTHEW.CHPPR1.KATL/0151` | waypoint ambiguity | `STL` |
| 64 | 29470 | `KONT.RAJEE4.MTBAL..CNERY..BLH.HYDRR1.KPHX/0047` | procedure-resolution error | bare DP dispatch |
| 65 | 30940 | `KORD..RAYNR..BRTMN..DNIKA..TAAYZ..MKG..MBS..KMBS/0035` | success | — |
| 66 | 31308 | `KOTH..LEDGE..CEC..KO60C..AMAKR.BDEGA4.KSFO/0055` | parser error | real `FIX_BASE.FIX_ID` treated as airway |
| 67 | 31666 | `KPCW..ACO..KAOO/0050` | success | — |
| 68 | 32204 | `KPHL..DITCH..LUIGI..HNNAH.Q450.JFK.ROBUC3.KBOS/0055` | airway-resolution error | published `Q450` rejected |
| 69 | 32549 | `KPHL..STOEN..REEFI..EMI.J48.CSN..FANPO.Q40.AEX.GESNR2.KIAH/0256` | airway-resolution error | published `Q40` rejected |
| 70 | 32588 | `KPHL..STOEN.Q75.GVE..AIROW.CHSLY7.KCLT/0110` | airway-resolution error | published `Q75` rejected |
| 71 | 32628 | `KPHL./.HAYDO..TRPOD.Q409.MRPIT..CEELY.Q172.YUTEE..SKWKR.SITTH3.KATL/0147` | success | — |
| 72 | 33356 | `KPHX.ZEPER2.RRSTA..DOVEE..BTY..RUSME.RAZRR5.KSJC/0132` | procedure-resolution error | bare DP dispatch |
| 73 | 33849 | `KPNS..NFD` | success | — |
| 74 | 33948 | `KPQI..MLT..KMHT/0123` | success | — |
| 75 | 34727 | `KRDU..KSVH/0028` | success | — |
| 76 | 35076 | `KRFD.BIXBY1.QUIZZ..COLIE..BULET.RUDDH3.KMCI/0055` | procedure-resolution error | bare DP dispatch |
| 77 | 35517 | `KROS..KRNH/0014` | success | — |
| 78 | 35624 | `KRSW.CSHEL8.CAMJO..CNTLR..GLAZR..IIU..MACES..VINNE..BRAVE..EXARR..HIGUH..KPWK/0244` | procedure-resolution error | bare DP dispatch |
| 79 | 35839 | `KSAF.ZIASE5.GUP..FLG.J10.HIPPI..GABBL.HLYWD1.KLAX/0146` | procedure-resolution error | bare DP dispatch |
| 80 | 36165 | `KSAN.ZZOOO4.MTBAL..LANCY..EKR..BFF..VIVID..FSD..ZZIPR.FYTTE7.KORD/0334` | procedure-resolution error | bare DP dispatch |
| 81 | 36525 | `KSAV..TILLS` | success | — |
| 82 | 36664 | `KSBN..HOSSA.VCTRZ2.KDTW/0028` | success | — |
| 83 | 36933 | `KSDF.HIDEY1.RAMRD..BNA..RQZ..NULLS..KBHM/0051` | procedure-resolution error | bare DP dispatch |
| 84 | 37100 | `KSDF.SPILR1.BNGIN..SHB..VHP..KG66K..KP75G..KP87A..DPR.J204.MLS..CONUK.KUSTR3.KBIL/0253` | procedure-resolution error | bare DP dispatch |
| 85 | 37301 | `KSEA..SEA..NORMY..MODDA..STEVS.Q148.WEDAK.Q152.ONL.J151.IRK..ENL..IIU.J8.DACOS..JARLO.GIBBZ5.KIAD/0435` | waypoint ambiguity | `SEA` |
| 86 | 37871 | `KSEM..KMOB/0048` | success | — |
| 87 | 38058 | `KSFO.NIITE4.SYRAH.Q128.JSICA..MLF..DVC..CIM..PNH..ADM..ELD..MERDN..ORRKK.GNDLF3.KATL/0414` | procedure-resolution error | bare DP dispatch |
| 88 | 38184 | `KSFO.SNTNA2.SYRAH.Q128.JSICA.Q128.TABLL..KU54O..WEEMN..KD60S..MOCTU..KD72Y..HUTEP..KP84E..ZANNA..KP87K..GRB..RUBKI..AHPAH..HANKK..PONCT.JFUND2.KBOS/0502` | procedure-resolution error | bare DP dispatch |
| 89 | 38230 | `KSFO.SSTIK5.SUSEY..AVE..EHF..KBFL/0040` | procedure-resolution error | bare DP dispatch |
| 90 | 39169 | `KSLC.RUGGD3.HOLTR..GTF..KGTF/0105` | procedure-resolution error | bare DP dispatch |
| 91 | 40474 | `KSUA.SNDLR3.SHEDS..ODDEL..SMELZ.Q110.JOKKY..WANDS..KBHM/0135` | procedure-resolution error | bare DP dispatch |
| 92 | 40712 | `KTAN..POU` | success | — |
| 93 | 41797 | `KTUS.BURRO5.BBALL..PXR..NAVHO..ARAYI..PDT.CHINS5.KSEA/0248` | procedure-resolution error | bare DP dispatch |
| 94 | 42315 | `KVGT..BTY` | success | — |
| 95 | 42634 | `KVRB..WILBA..KPBI/0014` | success | — |
| 96 | 43648 | `MMAS./.NLD.J22.LRD..KLRD` | missing NASR data | foreign airport |
| 97 | 43922 | `MMPR./.BECON..GUP..MTU..HLN..COUTS..EBGAL.EBGAL7.CYYC` | missing NASR data | foreign airports/procedure |
| 98 | 44080 | `MMUN./.MYDIA.M219.KNOST..DEANR..BRUTS.Q109.CAMJO..TWINS..PONZE.BANKR6.KCLT` | missing NASR data | foreign airport |
| 99 | 44466 | `MYNN..ZQA.G437.DYNAH.UG437.ULBAS.UM330.KANEX.R630.GCM..MWCR/0102` | missing NASR data | foreign airway system |
| 100 | 45904 | `TJSJ..SJU.RTE2.STT..TIST/0026` | missing NASR data | external Caribbean route system |

## Typed result/error policy

The successful result remains exactly
`tuple[tuple[float, float], ...]`; there is no sentinel, partial-path result,
or result-union wrapper. Resolution is fail-fast at the earliest route token
that cannot be resolved faithfully.

| Condition | Required public exception | Required structured context |
| --- | --- | --- |
| Unknown domestic NASR record | Existing `RecordNotFoundError` | `entity_type`, `identifier`, and applicable lookup `filters`. Use only after the token is classified as domestic and the relevant selected-cycle table was searched. |
| Ambiguous domestic record/procedure/path | Existing `AmbiguousRecordError` | `entity_type`, `identifier`, applicable `filters`, and bounded `candidates`. Never pick arbitrarily. |
| Recognized external/oceanic/coordinate/radial content outside the supported domestic contract | New `UnsupportedRouteContentError(OpenNASRError)` | `token`, zero-based `position`, `content_type` (`foreign_airport`, `oceanic_coordinate`, `radial_distance`, or `external_route`), and selected `cycle`. It must not subclass `RecordNotFoundError`: the record was not promised by the data source. |
| Malformed route text | New `MalformedRouteError(OpenNASRError)` | `route_text`, offending `token` when one exists, zero-based `position` when one exists, and a concise `reason`. Covers empty input, malformed separators/suffixes, and an airway without two endpoint tokens. Replace route-parser `ValueError`; do not use it for syntactically valid unsupported content. |
| Broken published connectivity | New `RouteConnectivityError(OpenNASRError)` | `entity_type` (`Airway`/`DepartureProcedure`/`StarProcedure`), `identifier`, `from_identifier`, `to_identifier`, and selected `cycle`. Raise only when the named published record and both endpoints exist but the selected-cycle rows do not yield one faithful ordered path. |

All three proposed types should be exported from `openNASR.exceptions` and
the package API when their production tasks land. They are intentionally
siblings under `OpenNASRError`: callers may catch the stable base, while
batch validation can distinguish unsupported coverage, invalid user text,
and internally broken published connectivity without parsing messages.
Missing tables/cycles remain the existing `TableNotFoundError` and
`CycleNotFoundError`; they are environment/data-lifecycle failures, not a
property of one route token.

Error precedence is: malformed lexical structure; recognized unsupported
content; record lookup/ambiguity; then connectivity after all participating
records exist. This prevents a foreign ICAO identifier from being reported
as an unknown domestic waypoint and prevents a missing endpoint record from
being mislabeled as broken connectivity.

## Domestic-only target and denominator

The Phase 1-5 release target is **at least 90% of the fixed 84-row domestic
NASR denominator (at least 76 successful routes), with no regression among
the 36 currently no-exception domestic rows**. One hundred percent (84/84)
is the stretch target. The baseline's raw domestic no-exception rate is
36/84 (42.9%); the 90% gate therefore requires at least 40 additional
domestic routes to convert successfully without losing an existing one.

The denominator is content-based and remains fixed across phase gates. A row
is excluded if faithfully converting it requires data or route constructs
outside the domestic NASR contract, even when an earlier domestic procedure
bug is the failure currently observed. Thus a later oceanic segment cannot
remain hidden behind a preceding bare-DP failure and later inflate or shrink
the denominator as bugs are fixed.

Sixteen canonical rows are excluded and reported separately:

| Exclusion class | Count | Zero-based source indices |
| --- | ---: | --- |
| Foreign/oceanic/external route content | 13 | `964`, `1837`, `4549`, `6867`, `19034`, `21402`, `24891`, `25943`, `43648`, `43922`, `44080`, `44466`, `45904` |
| Coordinate or radial-distance route points handled as separate Phase 6 coverage | 3 | `2271`, `14154`, `29272` |
| Total excluded | 16 | — |

Excluded rows still run and are reported by category; they are never silently
dropped from the 100-row report. Their current raw outcome is 2 no-exception
and 14 exceptions. These counts are not part of the domestic percentage and
improvements to them do not satisfy the Phase 1-5 target.

For the target, a “success” means the validation utility completes the whole
route and returns a non-empty ordered coordinate tuple without a typed error.
Once token-position diagnostics exist (T5.2), it must also confirm that every
non-suffix route component was consumed. A path produced by truncating the
route at `./.` or mistaking an embedded coordinate slash for the trailing
speed/altitude delimiter does not count, even if the current function returns
without raising. Curated exact-order fixtures remain the fidelity check; the
percentage is a coverage gate, not proof that every returned route is an
operationally valid flight path.

## Gate 2 review (2026-08-17)

**Decision: not approved.** The final review used production commit `4960111`
(`fix: retain exact dotted departure codes`), including T2.7 test commit
`42bf911` and its lint-only follow-up `d200241`. The focused command
`.venv/bin/pytest -q tests/test_flightplan.py
tests/test_route_regression_fixture.py` passed all 24 tests.

The canonical rerun again used the `2026-05-14` CSV cycle and one shared
`_WaypointResolver`. Raw coverage improved from 38/100 to 56/100, and the
fixed domestic denominator improved from 36/84 to 54/84. Eighteen former
failures now return paths and no former no-exception row regressed.

Root-cause categories moved as follows. Category growth after a preceding
procedure is fixed can mean the run reached a later defect; it does not imply
the newly visible defect was introduced by Phase 2.

| Category | T0.2 baseline | Gate 2 rerun | Change |
| --- | ---: | ---: | ---: |
| success | 38 | 56 | +18 |
| procedure-resolution error | 40 | 8 | -32 |
| airway-resolution error | 7 | 17 | +10 |
| waypoint ambiguity | 4 | 5 | +1 |
| parser error | 2 | 4 | +2 |
| missing NASR data | 9 | 10 | +1 |
| malformed input | 0 | 0 | 0 |

Phase 2 behavior is materially improved and its synthetic/cycle-shaped matrix
passes: bare and dotted DPs/STARs, DP-to-airway, airway-to-STAR,
procedure-only, the `GNDLF3` bare STAR, the `MCRAY2` plain-fix boundary, and a
mixed DP/direct/airway/navaid/STAR route are covered. The gate nevertheless
requires both procedure-resolution and parser-classification categories to
shrink. Procedure errors shrank sharply, but the original parser collisions
remain and two more valid `FIX_BASE.FIX_ID` values reached after procedure
expansion (`KM18K`, `KG66K`) are lexically treated as airways. Gate 2 therefore
remains closed pending contextual waypoint-before-airway dispatch for these
valid NASR fixes and a confirming canonical rerun.
