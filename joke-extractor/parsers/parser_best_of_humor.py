"""Parser for Best of Humor emails."""
# SEE EXAMPLE EMAIL AT BOTTOM OF FILE

from .email_data import EmailData, JokeData
from . import register_parser
import logging

# Configure logging to stderr for visibility in pipelines
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def _can_be_parsed_here(email: EmailData) -> bool:
    return False
    #return "bestofhumor.com" in email.from_header.lower()

@register_parser(_can_be_parsed_here)

def parse(email: EmailData) -> list[JokeData]:
    """
    Parse 'Best of Humor' email format.

    Jokes are embedded between visual separator lines like:
        +--------------...------------+
        or
        ++-...--++

    Each joke is the text *between* such lines (or between a line and email start/end).

    The email footer (signature, unsubscribe, newsletter sign-ups, promotions)
    is excluded. Only substantial jokes (≥2 lines, non-promotional) are returned.

    Parameters
    ----------
    email : EmailData
        Email to parse
        
    Returns
    -------
    list[JokeData]
        List of extracted jokes in JokeData.
    """
    # storage for all the jokes that are collected. This is the return variable
    jokes = []

    joke_submitter = "Shawn Thayer <shawn@bestofhumor.com>"

    lines = email.text.split('\n')
    joke_text = ''
    i = 0
    state = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        #logging.info(f"state {state}: {line}")
        match state:
            case 0:
                if ((stripped.startswith('+') and stripped.endswith('+')) or 
                    (stripped.startswith('~') and stripped.endswith('~')) or
                    (stripped.startswith('_') and stripped.endswith('_'))):
                    state += 1
                i += 1

            case 1:
                if ((stripped.startswith('+') and stripped.endswith('+')) or 
                    (stripped.startswith('~') and stripped.endswith('~')) or
                    (stripped.startswith('_') and stripped.endswith('_'))):
                    state += 1
                i += 1

            case 2:  # Collect until end marker `[...]`
                if ((stripped.startswith('+') and stripped.endswith('+')) or 
                    (stripped.startswith('~') and stripped.endswith('~')) or
                    (stripped.startswith('_') and stripped.endswith('_'))):

                    jokes.append(JokeData(text=joke_text.strip(), submitter=joke_submitter, title=''))
                    state = 1
                    joke_text = ''
                else:
                    if ('http' in stripped or
                        '<a' in stripped.lower() or
                        'mailto:' in stripped or
                        stripped.lower().startswith('subscribe') or
                        stripped.lower().startswith('join') or
                        stripped.lower().startswith('unsub') or
                        stripped.startswith('___') or
                        'Bestofhumor.com' in stripped or
                        'email4fun' in stripped):
                        pass
                    else:
                        joke_text += line + "\n"

                i += 1

    return jokes

import sys

if __name__ == "__main__":

    email = EmailData(
        from_header = "Subject: Best of Humor July 13th",
        subject_header = "From: \"Bestofhumor.com\" <shawn@bestofhumor.com>",
        text = """
Welcome to Best of Humor ---> http://www.bestofhumor.com
We are part of the email4fun.com network ---> http://www.email4fun.com
For FREE Fun E-mail, Visit http://sjMail.com

-------------- LIST INFORMATION -----------------
You are subscribed as: gcfl-submit@gcfl.net
To unsubscribe send an email to
<A href="mailto:bestofhumor-leave@list2.sjmail.com">unsubscribe</A>
Or go to:  http://www.bestofhumor.com/leave.html
Join Best of Humor:  http://www.bestofhumor.com/subscribe.html
-------------- LIST INFORMATION -----------------

NOTE:  We had some computer problems on our end the past couple days.  We 
are finalizing our move to a new lyris server.  Don't worry all of you are 
coming with me to hopefully a faster server

+---------------------------------------------------------------+
Win a Complete home theater!
It's a super System! A 53" Big Screen TV!

Surround Sound System, CD/DVD Player.
Two leather recliners.
What do you have to lose? Enter now!
This offer expires 08/04/00.
http://www.afreeplace.com/boh/super.htm
<a href="http://www.1freeplace.com/boh/super.htm">AOL link</a>
+---------------------------------------------------------------+

A painter, whitewashing the inner walls of a country outhouse,
had the misfortune to fall through the opening and land in the
muck at the bottom. He shouted, "Fire! Fire! Fire!" at the top
of his lungs.

The local fire department responded with alacrity, sirens
roaring as they approached the privy.

"Where's the fire?" called the chief.

"No fire," replied the painter as they pulled him out of the hole.

"But if I had yelled, 'Shit! Shit! Shit!' who would have rescued me?"

+---------------------------------------------------------------+
FREE E-MAIL ENTERTAINMENT
List World is the place to go to get all the free
newsletters you want! Join a free newsletter now!
http://www.listworld.net/index23b.cfm?refid=24
<A href="http://www.listworld.net/index23b.cfm?refid=24">FREE NEWSLETTERS</A>
+---------------------------------------------------------------+

Amanpreet was having marital problems. So he went to his

The shrink says "when you get home, throw down your
briefcase, run to her, embrace her, take off her clothes, and
yours, and make made passionate love to her."
In two weeks Preet was back in the shrink's office. The shrink
asked "How did it go?"

Preet said, "She didn't have anything to say, but her bridge
club got a kick out of it."

~~~~~~~~~~~~~~~~
Shawn Thayer
Best of Humor
http://www.bestofhumor.com
shawn@bestofhumor.com

_______  Bestofhumor.com Daily Humor  _______
You are subscribed as: gcfl-submit@gcfl.net
To unsubscribe send an email to 
mailto:leave-bestofhumor-284604L@list2.sjMail.com
Or go to:  http://www.bestofhumor.com/leave.html

We are part of the email4fun.com network ---> http://www.email4fun.com
"""
    )
    jokes = parse(email)


