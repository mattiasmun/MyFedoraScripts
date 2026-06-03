project(
  'kakurasu',
  'vala',
  version : '1.0.0',
  default_options : [
    'warning_level=2',
    'buildtype=release'
  ]
)

vala = meson.get_compiler('vala')

executable(
  'kakurasu',
  'solver/kakurasu.vala',
  dependencies : [
    dependency('json-glib-1.0')
  ],
  install : true
)
