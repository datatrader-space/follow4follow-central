def formatify_for_server(bot):
        from sessionbot.models import ChildBot
        from django.forms import model_to_dict
        if type(bot)==str:
                c=ChildBot.objects.all().filter(username=bot)
                if c:
                    bot=c[0]
    

        _bot = model_to_dict(bot)
        _bot.pop("created_on", None)
        _bot.pop("cookie")
        _bot.pop("profile_picture")
        _bot.pop("dob")
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
        return _bot