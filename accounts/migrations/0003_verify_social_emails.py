from django.db import migrations

UNUSABLE_PREFIX = '!'   # Django-ийн set_unusable_password() ийм тэмдэгтээр эхэлдэг


def verify_social_accounts(apps, schema_editor):
    """Google/Facebook-ээр үүссэн (нууц үггүй) бүртгэлийн имэйлийг баталгаажсан гэж тэмдэглэнэ.

    Эдгээр хэрэглэгч profile талбар нэмэгдэхээс өмнө нэвтэрсэн тул тэмдэглэгдээгүй үлдсэн.
    """
    User = apps.get_model('auth', 'User')
    Account = apps.get_model('accounts', 'Account')
    for user in User.objects.filter(password__startswith=UNUSABLE_PREFIX).exclude(email=''):
        account, _ = Account.objects.get_or_create(user=user, defaults={'phone_number': ''})
        if not account.email_verified:
            account.email_verified = True
            account.save(update_fields=['email_verified'])


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_profile_fields'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]
    operations = [migrations.RunPython(verify_social_accounts, migrations.RunPython.noop)]
