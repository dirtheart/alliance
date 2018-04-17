# Gets key ownership data from the ingressalliance.org API

import logging
import plugins
import requests
import time
import copy

logger = logging.getLogger(__name__)
_cache = {}

def _initialise(bot):
    plugins.register_admin_command(["ia"])

def ia(bot, event, *args):
    portal_search = " ".join(args).lower()
    ia_key = bot.get_config_suboption(event.conv_id, "ia_api_key")
    group_key = bot.get_config_suboption(event.conv_id, "ia_group")
    max_cache_age = bot.get_config_suboption(event.conv_id, "ia_cache_age") or 60 # minutes
    if not ia_key:
        yield from bot.coro_send_message(event.conv_id, "IA API key not defined: config.ia_api_key")
        return
    if not group_key:
        yield from bot.coro_send_message(event.conv_id, "IA group not defined: config.ia_group")
        return
    if group_key in _cache:
        age_minutes = (time.time() - _cache[group_key]['timestamp']) / 60
        keys = _cache[group_key]['keys']
        if age_minutes < max_cache_age:
            logger.debug("Using cache")
        else:
            try:
                keys = requests.get("https://beta.ingressalliance.org/api/getGroupKeys.php?key={}&gkey={}".format(ia_key, group_key)).json()
                _cache[group_key] = {'timestamp': time.time(), 'keys': keys}
            except:
                logger.debug("error trying to get keys from IA, falling back to cache")
    else:
        try:
            keys = requests.get("https://beta.ingressalliance.org/api/getGroupKeys.php?key={}&gkey={}".format(ia_key, group_key)).json()
            _cache[group_key] = {'timestamp': time.time(), 'keys': keys}
        except Exception as e:
            yield from bot.coro_send_message(event.conv_id, "Unable to get keys from IA")
            logger.error(e)
            return

    matched_portals = {}
    exact_match = False;
    require_exact = False;
    for record in keys:
        if (portal_search in record['portal_name'].lower()) or (portal_search in record['portal_address'].lower()):
            guid = record['portal_guid']
            if guid not in matched_portals:
                matched_portals[guid] = copy.copy(record)
                matched_portals[guid]['agents'] = []

            if (portal_search in record['portal_name'].lower()) or (portal_search in record['portal_address'].lower()):
                matched_portals[guid]['exact_match'] = True
                exact_match = True
            else:
                matched_portals[guid]['exact_match'] = False

            matched_portals[guid]['agents'].append("{}: {}".format(record['google_name'], record['agent_sum']))
    if len(matched_portals) > 50:
        if exact_match:
            require_exact = True
        else:
            yield from bot.coro_send_message(event.conv_id, "> 50 portals matched - be more specific")
            return
    if len(matched_portals) == 0:
        yield from bot.coro_send_message(event.conv_id, "No keys found")
        return
    outputString = ""
    for guid, record in matched_portals.items():
        if not(require_exact) or record['exact_match']:
            agents = record['agents']
            intellink = "https://www.ingress.com/intel?ll={},{}&z=17&pll={},{}".format(record['portal_latE6'], record['portal_lngE6'], record['portal_latE6'], record['portal_lngE6'])
            outputString += "<b>{}</b>\n{}\n<i>{}</i>\n".format(record['portal_name'], intellink, record['portal_address']) + "\n".join(agents) + "\n\n"
    outputString = outputString.strip("\n")
    yield from bot.coro_send_message(event.conv_id, outputString)
