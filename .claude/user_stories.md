# User Stories & Test Scenarios

Each scenario includes: preconditions, action, and expected outcome. Organized by feature area.

**User roles used throughout:**
- **User** — any server member without Administrator permission
- **Admin** — server member with Administrator permission
- **Bot Admin** — the user identified by `CONFIG.ADMIN_USER_ID`

---

## `/help` — Help Command

**H-1: User views help**
- Given: bot is running with extensions loaded
- When: User runs `/help`
- Then: a paginated embed dialog appears with one page per slash command and context menu command; admin-only commands are not shown; a select menu allows jumping between pages; the dialog times out after 5 minutes

**H-2: Admin views help**
- Given: invoker has Administrator permission
- When: Admin runs `/help`
- Then: all commands appear including admin-only commands (e.g. `/speak`, `/messages delete`, `/reload`); admin commands appear after non-admin commands in the select menu order

**H-3: Commands sorted by type**
- Given: multiple extension types are loaded
- When: help dialog is opened
- Then: regular slash commands appear first, context menu commands appear in the middle, admin slash commands appear last

**H-4: Each page shows parameter info**
- Given: a slash command has required and optional parameters
- When: its help page is displayed
- Then: each parameter is listed as a field showing its name, type, and whether it is optional

**H-5: Help dialog is user-scoped**
- Given: User A opened a `/help` dialog
- When: User B clicks the paginator buttons on that dialog
- Then: bot responds ephemerally telling User B the dialog isn't theirs, and instructs them to use `/help` themselves

---

## `/role` — Role Management

**R-1: Create a new joinable role**
- Given: no role named "League" exists
- When: User runs `/role create name:League`
- Then: a new mentionable role with zero permissions is created; bot confirms with a role mention

**R-2: Create a role with a duplicate name**
- Given: a role named "League" already exists
- When: User runs `/role create name:League`
- Then: bot replies with a user-friendly error; no new role is created

**R-3: Delete a joinable role (sole member)**
- Given: a joinable role "League" exists; invoker is the only member
- When: User runs `/role delete role:@League`
- Then: role is deleted; bot confirms

**R-4: Delete a role with other members**
- Given: a joinable role "League" has 2+ members
- When: any member runs `/role delete role:@League`
- Then: bot rejects with an error indicating others are still in the role

**R-5: Delete a non-joinable role**
- Given: a role "Moderator" has permissions or is not mentionable
- When: User runs `/role delete role:@Moderator`
- Then: bot rejects with "You cannot request to delete this role"; role is not deleted

**R-6: Join — dropdown shows available roles**
- Given: joinable roles "League" and "Chess" exist; User is not in either
- When: User runs `/role join`
- Then: an ephemeral dropdown appears listing both roles

**R-7: Join — dropdown excludes already-joined roles**
- Given: User is already in "League" but not "Chess"
- When: User runs `/role join`
- Then: dropdown shows only "Chess"

**R-8: Join — no available roles**
- Given: User is already in all joinable roles (or none exist)
- When: User runs `/role join`
- Then: bot replies with an error; no dropdown shown

**R-9: Join — successful selection**
- Given: join dropdown is open with "League" and "Chess"
- When: User selects both and confirms
- Then: User is added to both roles; bot confirms ephemerally

**R-10: Join — role deleted between dropdown open and selection**
- Given: join dropdown is open; "League" is deleted before selection
- When: User selects "League"
- Then: bot reports "League" as failed; does not crash; other valid selections still succeed

**R-11: Leave — dropdown shows joined roles**
- Given: User is in "League" but not "Chess"
- When: User runs `/role leave`
- Then: ephemeral dropdown shows only "League"

**R-12: Leave — no joinable roles to leave**
- Given: User is not in any joinable roles
- When: User runs `/role leave`
- Then: bot replies with an error; no dropdown shown

**R-13: Leave — successful selection**
- Given: leave dropdown is open
- When: User selects a role and confirms
- Then: User is removed from the role; bot confirms ephemerally

---

## `/channel create` — Channel Management

**C-1: Create a text channel (no category)**
- Given: no channel named "general-two" exists
- When: User runs `/channel create name:general-two`
- Then: a new text channel is created at the server root; bot confirms with channel mention

**C-2: Create a text channel under a category**
- Given: a category "Gaming" exists
- When: User runs `/channel create name:league category:Gaming`
- Then: new text channel is created nested under "Gaming"

**C-3: Create channel with duplicate name**
- Given: a text channel named "general" already exists
- When: User runs `/channel create name:general`
- Then: bot rejects with an error mentioning the existing channel; no channel created

---

## Voice Announcer — Auto-management (requires `VOICE_ANNOUNCER` feature flag)

**V-1: First user joins a voice channel — bot follows**
- Given: VOICE_ANNOUNCER is enabled; bot is not in any VC
- When: a user joins any voice channel
- Then: bot joins that voice channel; no announcement is played (bot just arrived)

**V-2: User joins bot's current voice channel — announcement**
- Given: bot is already in "Gaming VC" with one user
- When: a second user joins "Gaming VC"
- Then: bot plays TTS: `"<username> has joined."`

**V-3: User moves into bot's voice channel — announcement**
- Given: bot is in "Gaming VC"; a user moves from "Chill VC" to "Gaming VC"
- When: VoiceStateUpdate fires
- Then: bot plays TTS: `"<username> has joined."`

**V-4: User moves out of bot's channel — bot follows to most active VC**
- Given: bot is in "Gaming VC" with only User A; another VC "Chill VC" has 2 users
- When: User A moves to "Chill VC"
- Then: bot moves to "Chill VC" and plays TTS: `"<bot username> has joined."`

**V-5: Last user leaves bot's channel — others remain elsewhere — bot moves**
- Given: bot is in "Gaming VC" alone after the last user left; "Chill VC" has users
- When: VoiceUserLeave fires
- Then: bot moves to "Chill VC" and announces arrival

**V-6: Last user leaves bot's channel — no active VCs — bot disconnects**
- Given: bot is in "Gaming VC"; last user leaves; no other VCs have users
- When: VoiceUserLeave fires
- Then: bot disconnects from "Gaming VC"; no TTS played

**V-7: User leaves a different channel (not bot's) — bot ignores**
- Given: bot is in "Gaming VC"; a user leaves "Chill VC"
- When: VoiceUserLeave fires
- Then: bot takes no action

**V-8: Bot restarts while users are in a voice channel**
- Given: VOICE_ANNOUNCER is enabled; "Gaming VC" has active users at startup
- When: bot completes startup
- Then: bot joins "Gaming VC" and plays TTS: `"<bot username> restarted."`

**V-9: VOICE_ANNOUNCER feature disabled — no auto-behaviour**
- Given: the bot's application description does not contain `"voice_announcer"`
- When: any voice state event fires
- Then: bot does not join, move, or play any announcements

**V-10: Bot movement is ignored by voice listeners**
- Given: VOICE_ANNOUNCER is enabled
- When: the bot itself moves between voice channels
- Then: no announcement is triggered; no recursive join logic fires

---

## Username Enforcement — Auto-nickname (users.py)

**U-1: Member sets nickname without their username**
- Given: User "shajesh" sets nickname "Peanut"
- When: MemberUpdate fires
- Then: bot updates nickname to "Peanut [shajesh]"

**U-2: Member sets nickname already containing their username**
- Given: User "shajesh" sets nickname "Big shajesh"
- When: MemberUpdate fires
- Then: bot makes no change

**U-3: Member resets nickname to none**
- Given: User removes their nickname
- When: MemberUpdate fires with nick = None
- Then: bot makes no change

**U-4: New nickname would exceed 32 characters**
- Given: User "shajesh" sets nickname "A very long nickname indeed" (combined result > 32 chars)
- When: MemberUpdate fires
- Then: bot resets their nickname to None and DMs them explaining the character limit and how many characters they have available

**U-5: Bot lacks permission to edit nickname (e.g. for admins)**
- Given: target member has higher role than bot
- When: bot attempts to edit or reset the nickname
- Then: HTTP 50013 error is silently swallowed; no crash; no DM sent

---

## `/speak` — Admin Message

**SP-1: Admin makes bot speak**
- Given: invoker has Administrator permission
- When: Admin runs `/speak message:Hello everyone`
- Then: bot sends "Hello everyone" in the current channel

**SP-2: Non-admin attempt**
- Given: invoker does not have Administrator permission
- Then: `/speak` is not visible or usable in the command picker (hidden by default_permissions)

---

## `/messages delete` — Bulk Delete

**MD-1: Admin deletes messages**
- Given: invoker has Administrator permission; channel has 10+ messages
- When: Admin runs `/messages delete amount:5`
- Then: 5 most recent messages are deleted; bot replies ephemerally confirming count

**MD-2: Default deletes one message**
- Given: invoker has Administrator permission
- When: Admin runs `/messages delete` (no amount)
- Then: 1 message is deleted

**MD-3: Non-admin attempt**
- Given: invoker does not have Administrator permission
- Then: `/messages delete` is not visible or usable in the command picker (hidden by default_permissions)

---

## `/quote` — Manual Quote

**Q-1: Quote a valid message**
- Given: a valid Discord message link from this server
- When: User runs `/quote link:<message-link>`
- Then: bot sends an embed showing the quoted message's author, content, any image, timestamp, source channel, and a "View Original" link

**Q-2: Invalid or non-Discord link**
- Given: a string that is not a discord message URL
- When: User runs `/quote link:https://example.com`
- Then: bot replies with a user-facing error

**Q-3: Link from a different server**
- Given: a valid Discord link but from a different guild
- When: User runs `/quote`
- Then: bot replies with an error ("Cannot quote messages from other servers")

---

## Auto-quote — Passive Message Listener

**AQ-1: Message contains a Discord message link**
- Given: a message is posted with a `discord.com/channels/...` link
- When: MessageCreate fires
- Then: bot replies with a quote embed for the linked message

**AQ-2: Message contains multiple Discord links**
- Given: a message has two valid Discord message links
- When: MessageCreate fires
- Then: bot quotes only the first valid link

**AQ-3: Linked message is unresolvable**
- Given: message contains a link to a deleted or inaccessible message
- When: MessageCreate fires
- Then: bot silently skips that link; no reply sent

---

## Auto-fix Twitter Links — Passive Listener

**TW-1: Message contains a twitter.com link**
- Given: a user posts a message with `https://twitter.com/...`
- When: MessageCreate fires
- Then: bot replies with the message content reformatted as a blockquote with `fxtwitter.com` substituted; original Twitter embed is suppressed

**TW-2: Message contains an x.com link**
- Given: a user posts a message with `https://x.com/...`
- When: MessageCreate fires
- Then: same as TW-1 with fxtwitter substitution

**TW-3: Message contains no Twitter/X links**
- Given: a normal message with no Twitter links
- When: MessageCreate fires
- Then: bot takes no action

---

## League Ping Flow — Passive Listener + Interactions

**LP-1: Message mentions the League role — bot responds**
- Given: `CONFIG.LEAGUE_ROLE_ID` is set; a message mentions the League role
- When: MessageCreate fires
- Then: bot replies with an availability dropdown (I'm down / Aram only / Ranked only / If penta / Later / Nah) and a "Ping to gather" button

**LP-2: User selects availability option**
- Given: the league ping check message is visible
- When: User selects "I'm down"
- Then: the bot's message content is updated to append the user's mention to the "I'm down" row

**LP-3: User changes their selection**
- Given: user previously selected "I'm down"
- When: User selects "Aram only"
- Then: their mention is removed from "I'm down" row and appended to "Aram only" row

**LP-4: User selects "Later" — time modal appears**
- Given: league check message is visible
- When: User selects "Later"
- Then: a modal appears asking "When?"; on submit, mention + time (if provided) is appended to the "Later" row

**LP-5: Ping to gather — Ranked**
- Given: users have responded; invoker clicks "Ping to gather" → selects "Ranked"
- When: callback fires
- Then: bot replies mentioning all users who responded (excluding "Aram only" and "Nah" respondents)

**LP-6: Ping to gather — Aram**
- Given: same setup; invoker selects "Aram"
- Then: bot pings all users except "Ranked only" and "Nah"

**LP-7: Ping to gather — Either**
- Given: same setup; invoker selects "Either"
- Then: bot pings all users except "Nah"

**LP-8: LEAGUE_ROLE_ID not configured**
- Given: `CONFIG.LEAGUE_ROLE_ID` is None
- When: any message is posted mentioning any role
- Then: bot does not respond with a league check

---

## `/emoji` — Emoji Request (Slash Command)

**E-1: Valid emoji request**
- Given: user attaches a valid PNG < 256 KB with a valid alphanumeric shortcut
- When: User runs `/emoji shortcut:peanut emoji:<attachment>`
- Then: bot DMs the Bot Admin with the request details and Approve/Deny buttons; user receives ephemeral confirmation

**E-2: Invalid file type**
- Given: user attaches a PDF or non-image file
- When: User runs `/emoji`
- Then: bot responds with an error specifying valid types (PNG, JPEG, GIF)

**E-3: File too large**
- Given: user attaches an image larger than 256 KB
- When: User runs `/emoji`
- Then: bot responds with an error indicating the size limit

**E-4: Invalid shortcut — non-alphanumeric characters**
- Given: shortcut contains spaces or special characters (e.g. "my emoji!")
- When: User runs `/emoji shortcut:my emoji!`
- Then: bot responds with an error explaining valid shortcut format

**E-5: Invalid shortcut — too short**
- Given: shortcut is a single character
- When: User runs `/emoji shortcut:a`
- Then: bot responds with a validation error

**E-6: Admin approves emoji**
- Given: an emoji request DM is open with Approve/Deny buttons
- When: Bot Admin clicks "Approve"
- Then: emoji is created in the server using the image URL; requester is notified in their original channel; Approve/Deny buttons are disabled on the admin DM

**E-7: Admin rejects emoji**
- Given: an emoji request DM is open
- When: Bot Admin clicks "Deny"
- Then: a modal appears asking for a rejection reason; on submit, requester is notified with the reason in their original channel; buttons disabled on the admin DM

---

## "Convert to Emoji" — Context Menu

**CE-1: Right-click message with 1 image**
- Given: a message has 1 image attachment
- When: User selects "Convert to Emoji" from the right-click context menu
- Then: a modal appears with 1 shortcut field labelled with the filename

**CE-2: Right-click message with multiple images**
- Given: a message has 3 image attachments
- When: User selects "Convert to Emoji"
- Then: modal appears with 3 shortcut fields (max 5 supported)

**CE-3: Right-click message with no images**
- Given: a message has no image attachments or embeds
- When: User selects "Convert to Emoji"
- Then: bot responds with an error

**CE-4: Right-click message with > 5 images**
- Given: a message has 6+ images
- When: User selects "Convert to Emoji"
- Then: bot responds with an error (max 5)

**CE-5: Leave some shortcut fields blank**
- Given: modal has 3 shortcut fields; user fills 2, leaves 1 blank
- When: modal is submitted
- Then: 2 emoji requests are sent; the blank one is skipped; no error for the skipped image

**CE-6: Mixed valid and invalid requests**
- Given: modal submitted with 2 valid shortcuts and 1 invalid one
- When: requests are processed concurrently
- Then: valid ones are sent to admin; invalid one's error is reported back ephemerally; valid ones still proceed

---

## `/random` — Random Number

**RN-1: Generate a random number**
- Given: valid min and max
- When: User runs `/random min:1 max:100`
- Then: bot sends a message showing the range and a result in a code block, with a "Randomize Again" button

**RN-2: Min greater than max**
- Given: min=10, max=5
- When: User runs `/random min:10 max:5`
- Then: bot responds with a user-facing error

**RN-3: Re-randomize**
- Given: a `/random` result message with "Randomize Again" button
- When: User (any) clicks "Randomize Again"
- Then: a new result is appended to the same message in the code block; the previous result is italicised; the button remains

---

## `/roll` — Dice Roll

**RL-1: Valid dice roll**
- Given: standard dice notation
- When: User runs `/roll roll:2d6+3`
- Then: bot sends a message showing the notation, individual die results, and total; a "Roll Again" button is attached

**RL-2: Simple roll**
- When: User runs `/roll roll:d20`
- Then: result is a single value 1-20; modifier of 0 not shown; "Roll Again" button present

**RL-3: Invalid notation**
- When: User runs `/roll roll:banana`
- Then: bot responds with a user-facing error

**RL-4: Re-roll**
- Given: a `/roll` result message with "Roll Again" button
- When: User clicks "Roll Again"
- Then: new roll result appended; previous result italicised; button remains

---

## `/stock` — Stock Lookup (requires `ALPHAV_CONNECTED` config)

**S-1: Look up a valid ticker**
- Given: ALPHAV_CONNECTED config is valid
- When: User runs `/stock ticker:AAPL`
- Then: bot sends an embed with the stock symbol, close price, previous close, price diff (coloured diff block), a graph image (if ≥2 data points), and a link to Yahoo Finance

**S-2: Ticker autocomplete**
- Given: User starts typing in the ticker field
- When: autocomplete is triggered
- Then: matching symbol suggestions appear (note: rate-limited; may not always respond)

**S-3: Rate limit hit**
- Given: Alpha Vantage returns a rate limit response
- When: User runs `/stock`
- Then: bot replies with a user-friendly error telling them to try again later

**S-4: Extension not loaded without config**
- Given: `ALPHAV_API_URL` or `ALPHAV_KEY` is not set
- When: bot starts up
- Then: `/stock` command does not appear; warning is logged; no crash

---

## `/minecraft` — Minecraft Server Commands (requires `MC_CONFIG`)

**M-1: Server is online**
- Given: Minecraft server is running and reachable
- When: User runs `/minecraft status`
- Then: ephemeral embed shows green status, player count, server version, server address, and server icon thumbnail

**M-2: Server is offline**
- Given: Minecraft server is not reachable (connection refused)
- When: User runs `/minecraft status`
- Then: ephemeral embed shows red status and "Offline" field

**M-3: Server status unknown error**
- Given: an unexpected error occurs querying the server
- When: User runs `/minecraft status`
- Then: ephemeral embed shows black/error status; Bot Admin receives a DM with the error traceback

**M-4: Link a valid Minecraft account**
- Given: "Notch" is a valid Mojang username
- When: User runs `/minecraft link username:Notch`
- Then: bot whitelists "Notch" on the server via Tailscale SSH; sends confirmation message

**M-5: Link an invalid username**
- Given: "xXFakeUserXx" does not exist in the Mojang API
- When: User runs `/minecraft link username:xXFakeUserXx`
- Then: bot responds with a user-facing error

**M-6: Whitelist command fails**
- Given: Tailscale SSH command returns an error
- When: User runs `/minecraft link`
- Then: bot responds with a user-facing error

**M-7: Unlink a Minecraft account**
- Given: "Notch" is a valid Mojang username
- When: User runs `/minecraft unlink username:Notch`
- Then: bot removes "Notch" from the whitelist via Tailscale SSH; sends confirmation

**M-8: Extension not loaded without config**
- Given: `MC_SERVER_IP` or `MC_TS_HOST` is not set
- When: bot starts up
- Then: `/minecraft` commands do not appear; warning is logged; no crash

---

## `/reload` — Dev-Only Extension Reload (local environment only)

**L-1: Admin reloads an extension**
- Given: bot is running in local environment; invoker has Administrator permission
- When: Admin runs `/reload ext:peanuts_bot.extensions.roles`
- Then: the roles extension is reloaded; bot responds ephemerally confirming reload

**L-2: Non-admin attempt**
- Given: bot is running in local environment
- When: User without Administrator permission runs `/reload`
- Then: Discord blocks the command (permissions-gated)

**L-3: Command not available in production**
- Given: `CONFIG.IS_LOCAL` is False
- When: bot starts up
- Then: `/reload` command is not registered; does not appear in Discord

---

## Cross-cutting: Error Handling & Infrastructure

**X-1: BotUsageError in any command**
- Given: a command raises `BotUsageError("specific message")`
- When: the error is triggered
- Then: user receives an ephemeral reply with that exact message; Bot Admin receives no DM; error does not propagate further

**X-2: Unexpected system error in a command**
- Given: an unhandled exception occurs in a command handler
- When: the error is triggered
- Then: user receives an ephemeral "Sorry, something went wrong" message; Bot Admin receives a DM embed with the full traceback (BOT_TOKEN redacted); error is re-raised to logs

**X-3: Health probe**
- Given: `CONFIG.HEALTH_PROBE` is True; bot is running
- When: GET `/ping` is called on port 8000
- Then: response is `{"message": "pong"}` with HTTP 200

**X-4: Health probe not started when disabled**
- Given: `CONFIG.HEALTH_PROBE` is False
- When: bot starts
- Then: no server is listening on port 8000

**X-5: Stale slash commands cleaned up on startup**
- Given: a slash command was removed from the code between deployments
- When: bot starts with `delete_unused_application_cmds=True`
- Then: the removed command no longer appears in Discord after startup

**X-6: All extensions implement HelpCmdProto**
- Given: a new extension is added without a `get_help_color()` static method
- When: bot starts up
- Then: startup fails with a `RuntimeError` naming the non-compliant extension
