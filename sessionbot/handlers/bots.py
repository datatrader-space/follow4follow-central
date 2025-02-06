def formatify_for_server(bot):
        from sessionbot.models import ChildBot
        from django.forms import model_to_dict
        print(bot)
        if type(bot)==str:
                c=ChildBot.objects.all().filter(username=bot)
                if c:
                    bot=c[0]
                else:
                       return False
    
        if not bot.uuid:
               import uuid
               bot.uuid=uuid.uuid1()
        _bot = model_to_dict(bot)
        _bot.pop("created_on", None)

      
        _bot.pop('followers')
        _bot.pop('following')
        _bot.pop('post_count')
        _bot.pop('first_name')
        _bot.pop('last_name')
        _bot.pop('state')
        _bot.pop('challenged')
        _bot.pop('logged_in_on_servers')
        _bot.pop('customer')
        _bot.pop('bio')
        
        _bot["device"] = bot.device.serial_number if bot.device else False
        _bot.pop('email_provider')
        _bot.pop('id')
        _bot['uuid']=str(_bot.get('uuid'))
        return _bot