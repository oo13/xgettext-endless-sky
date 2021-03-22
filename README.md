# xgettext-endless-sky
Utilities to extract translatable texts from the program and data files of of [Endless Sky](https://github.com/endless-sky/endless-sky) and its plugins. You can use it in [an unofficial translatable version](https://github.com/endless-sky/endless-sky/issues/558#issuecomment-622351133) of Endless Sky.
You need python3, and some convenient scripts run on sh.

## cmd/make_source_pot
A wrapper script to extract translatable texts from the sources of Endless Sky.
This script uses xgettext.

Example:
```
% cmd/make_source_pot /usr/src/endless-sky/source > endless-sky-source.pot
```

## cmd/make_data_pot
A wrapper script to extract translatable texts from the data files of Endless Sky and its plugins.
This script uses xgettext.endless_sky_data.

Example:
```
% cmd/make_data_pot /usr/src/endless-sky > endless-sky-data.pot
```

## cmd/xgettext.endless_sky_data
This program extracts translatable texts from the data files of Endless Sky and its plugins.

Example:
```
% cmd/xgettext.endless_sky_data -o endless-sky-data.pot *.txt
```

## cmd/check_translated_data
This program shows data files replaced translatable texts with translated.
Note: Some texts, such as the outfit's and mission's names, are not replaced.

Example:
```
% cmd/check_translated_data -p endless-sky-data-ja.po *.txt | less
```
