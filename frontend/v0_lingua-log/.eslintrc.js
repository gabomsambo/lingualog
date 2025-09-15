module.exports = {
  extends: [
    'next/core-web-vitals',
    'plugin:i18next/recommended'
  ],
  plugins: ['i18next'],
  rules: {
    // Forbid literal strings in JSX (except for specific cases)
    'i18next/no-literal-string': [
      'error',
      {
        markupOnly: true, // Only check JSX elements
        ignoreAttribute: [
          'className',
          'class',
          'style',
          'type',
          'id',
          'role',
          'tabIndex',
          'aria-label',
          'aria-labelledby',
          'aria-describedby',
          'data-testid',
          'data-cy',
          'href',
          'src',
          'alt',
          'name',
          'value',
          'placeholder',
          'key',
          'ref',
          'htmlFor',
          'accept',
          'method',
          'target',
          'rel',
          'width',
          'height',
          'viewBox',
          'fill',
          'd',
          'stroke',
          'strokeWidth',
          'strokeLinecap',
          'strokeLinejoin'
        ],
        ignoreCallee: [
          'console.log',
          'console.error',
          'console.warn',
          'console.info',
          'console.debug',
          'require',
          'import'
        ],
        ignoreProperty: [
          'className',
          'style',
          'type',
          'id',
          'role',
          'tabIndex'
        ]
      }
    ]
  },
  overrides: [
    {
      // Disable literal string checks for specific files
      files: [
        '**/*.config.{js,ts,mjs}',
        '**/next.config.{js,ts,mjs}',
        '**/tailwind.config.{js,ts}',
        '**/postcss.config.{js,ts,mjs}',
        '**/*.test.{js,ts,tsx}',
        '**/*.spec.{js,ts,tsx}',
        '**/lib/utils.ts',
        '**/lib/auth.ts',
        '**/lib/supabase.ts',
        '**/components/ui/**/*.{ts,tsx}',
        '**/i18n/**/*.{ts,tsx}',
        '**/types/**/*.{ts,tsx}',
        '**/hooks/**/*.{ts,tsx}',
        '**/app/globals.css',
        '**/styles/**/*.css'
      ],
      rules: {
        'i18next/no-literal-string': 'off'
      }
    }
  ]
}
