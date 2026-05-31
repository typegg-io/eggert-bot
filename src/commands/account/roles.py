import discord
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from database.typegg.users import get_quote_bests
from utils.errors import BotError
from utils.flags import Flags
from utils.messages import Page, Message
from utils.strings import get_argument

info = {
    "name": "roles",
    "aliases": ["role"],
    "description": "View available achievement roles and your progress, or claim one.",
    "parameters": "[role_name]",
    "examples": [
        "-roles",
        "-roles masochist"
    ],
}

ACHIEVEMENT_ROLES = {
    "masochist": {
        "role_name": "Masochist",
        "description": "Type all 100 masochist quotes",
        "total": 100,
    },
}


def check_masochist(user_id: str) -> tuple[int, int]:
    quote_bests = get_quote_bests(user_id, columns=["quoteId"], flags=Flags(status="any"))
    completed_ids = {qb["quoteId"] for qb in quote_bests}
    completed = len(MASOCHIST_QUOTE_IDS & completed_ids)
    return completed, len(MASOCHIST_QUOTE_IDS)


ROLE_CHECKS = {
    "masochist": check_masochist,
}


class Roles(Command):
    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    async def roles(self, ctx: BotContext, role_name: str = None):
        if not ctx.guild:
            raise BotError("Server Only", "This command can only be used in the server.")

        profile = await self.get_profile(ctx, races_required=False)

        if role_name is None:
            await list_roles(ctx, profile)
        else:
            key = get_argument(set(ACHIEVEMENT_ROLES), role_name, _raise=False)
            if not key:
                role_list = ", ".join(f"`{k}`" for k in ACHIEVEMENT_ROLES)
                raise BotError("Unknown Role", f"Available roles: {role_list}")
            await claim_role(ctx, profile, key)


async def list_roles(ctx: BotContext, profile: dict):
    lines = []
    for key, role in ACHIEVEMENT_ROLES.items():
        completed, total = ROLE_CHECKS[key](profile["userId"])
        has_role = discord.utils.get(ctx.author.roles, name=role["role_name"]) is not None
        status = "✅" if has_role else f"{completed}/{total}"
        lines.append(f"**{role['role_name']}** - {role['description']} ({status})")

    message = Message(ctx, Page(
        title="Achievement Roles",
        description="\n".join(lines),
    ))
    await message.send()


async def claim_role(ctx: BotContext, profile: dict, key: str):
    role_info = ACHIEVEMENT_ROLES[key]

    discord_role = discord.utils.get(ctx.guild.roles, name=role_info["role_name"])
    if not discord_role:
        raise BotError("Role Not Found", f"The `{role_info['role_name']}` role doesn't exist in this server.")

    if discord.utils.get(ctx.author.roles, name=role_info["role_name"]):
        message = Message(ctx, Page(
            title="Already Claimed",
            description=f"You already have the **{role_info['role_name']}** role.",
        ))
        return await message.send()

    completed, total = ROLE_CHECKS[key](profile["userId"])

    if completed < total:
        message = Message(ctx, Page(
            title=role_info["role_name"],
            description=f"{role_info['description']}\n\n**Progress:** {completed}/{total}",
        ))
        return await message.send()

    await ctx.author.add_roles(discord_role)
    message = Message(ctx, Page(
        title=f"{role_info['role_name']} Unlocked!",
        description=f"You've been awarded the **{role_info['role_name']}** role.",
    ))
    await message.send()


MASOCHIST_QUOTE_IDS = {*"""
ttnight_6698
fiofyww_3003
oasanaa_8555
tuchotc_8080
tn_1141
agaacad_6131
c2scags_0141
yitmsrh_0411
oatouco_0694
5652848_4032
ltbkoaj_8262
tipdiac_0197
fcapasp_3101
l_2740
tcwctrt_1633
dpvuvpv_8743
rbyogyo_1135
tatcac0_1805
itssddy_1646
hhghghh_4739
fiitfcc_8185
bgcbv3g_7574
yotdaui_0192
cdreaat_1259
aiottpi_8417
toniea__4834
psa12zj_8889
icoahby_6195
lobfnfl_9914
cicbdit_0404
tsoaafo_1609
tasmojt_8685
aalrrtl_8572
paasoac_6945
hfiiacw_5103
ttotkfb_7833
tfboaow_1420
lylahhw_3157
thorsbc_2466
tapipuo_2550
a5mjdpa_6632
noogggg_0887
accc2td_4540
wtngamn_7486
vivahvv_4965
potumcf_3047
1btssov_5424
nttgewo_5373
atcpwtv_4784
dmemdmf_8062
tvareot_4971
eyvgtqy_2644
3ttaa1p_1517
ycnqptb_9823
tfgostc_0544
bi2jyod_5871
tptwgfa_4935
atwmots_9726
78o8d9b_8881
hptqmme_4489
cptptpa_6337
atcmcbo_7232
14bweap_8206
tuawpoa_7911
oipbnot_2900
enifnim_7344
kssssnf_2301
fkkit3s_9160
n91gbbe_6825
hdysdwt_4310
tscysui_4765
tijgnjl_6472
aarwaat_1214
recpdsl_7773
rdfcxsp_8241
brpkmer_4482
tod2gdp_9035
srm_0067
aaaasaa_3544
pllhdbg_3413
t1neott_0528
fcauita_7693
nrikirt_3774
ptptstt_3036
bhdbhd0_3477
2481361_1610
cd1c1sp_9469
a_3355
a_5355
1234567_7477
caacvrp_8468
s1itsua_0000
1s22ote_6857
fowptic_6392
gtkyk1k_4082
t4tctpo_7668
9ce2eht_4344
tpfbfpp_2063
flniahf_1627
mgggggl_6932
""".split("\n")[1:-1]}
