import pluginVue from 'eslint-plugin-vue'
import ts from 'typescript-eslint'
import vueParser from 'vue-eslint-parser'

export default ts.config(
    // Global ignores
    {
        ignores: ['dist/**', 'node_modules/**', 'PROOF_PACK_FINAL/**']
    },
    // TypeScript files (.ts, .js)
    {
        files: ['**/*.ts', '**/*.js'],
        extends: [...ts.configs.recommended],
        languageOptions: {
            parser: ts.parser,
            sourceType: 'module'
        },
        rules: {
            '@typescript-eslint/no-explicit-any': 'off',
            '@typescript-eslint/no-unused-vars': 'off',
            'no-unused-vars': 'off'
        }
    },
    // Vue files (.vue)
    {
        files: ['**/*.vue'],
        extends: [
            ...pluginVue.configs['flat/recommended'],
            ...ts.configs.recommended
        ],
        languageOptions: {
            parser: vueParser,
            parserOptions: {
                parser: ts.parser,
                sourceType: 'module',
                extraFileExtensions: ['.vue']
            }
        },
        rules: {
            'vue/multi-word-component-names': 'off',
            'vue/no-v-html': 'off',
            'vue/no-unused-vars': 'warn',
            '@typescript-eslint/no-explicit-any': 'off',
            '@typescript-eslint/no-unused-vars': 'warn'
        }
    }
)
