# Contributing

Thanks for considering an improvement. Small, focused changes are easiest to
review: describe the user problem first, then the command or behavior you want
to improve.

Before opening a pull request, run:

```bash
bash -n bin/obs lib/*.sh install.sh
python3 -m unittest discover -s tests -v
```

Please avoid adding personal vault paths, OAuth credentials, tokens, or notes
to commits. New user-facing commands should have an `obs help` entry and a
README example when appropriate.
