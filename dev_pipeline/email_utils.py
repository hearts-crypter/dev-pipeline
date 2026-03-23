import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

ENV_PATH = Path('/home/ahjc/infra/.env')


def load_env(path: Path = ENV_PATH) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()
    return env


def send_email(to_addr: str, subject: str, body: str) -> None:
    env = load_env()
    email_address = env.get('EMAIL_ADDRESS', 'heartscrypter@havnis.com')
    email_password = env.get('EMAIL_PASSWORD')
    smtp_host = env.get('SMTP_HOST')
    smtp_port = int(env.get('SMTP_PORT', '587'))
    smtp_secure = str(env.get('SMTP_SECURE', 'false')).lower() in ('1', 'true', 'yes')

    missing = [k for k, v in {
        'EMAIL_PASSWORD': email_password,
        'SMTP_HOST': smtp_host,
    }.items() if not v]
    if missing:
        raise RuntimeError(f"Missing required env values: {', '.join(missing)}")

    msg = EmailMessage()
    msg['From'] = email_address
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg.set_content(body)

    if smtp_secure:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=30) as server:
            server.login(email_address, email_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(email_address, email_password)
            server.send_message(msg)
