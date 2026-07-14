import { config } from 'md-editor-v3'

export function isAllowedPublicImageUrl(value: string) {
  try {
    const url = new URL(value)
    return url.protocol === 'https:' && Boolean(url.hostname) && !url.username && !url.password
  } catch {
    return false
  }
}

config({
  markdownItConfig(markdown) {
    markdown.set({ html: false, linkify: true, breaks: true })

    const renderImage = markdown.renderer.rules.image
    markdown.renderer.rules.image = (tokens, index, options, environment, renderer) => {
      const token = tokens[index]
      const source = token?.attrGet('src') ?? ''
      if (!isAllowedPublicImageUrl(source)) {
        return '<span class="markdown-image-warning">图片未显示：仅支持 HTTPS 公网图片地址。</span>'
      }
      token?.attrSet('loading', 'lazy')
      token?.attrSet('referrerpolicy', 'no-referrer')
      return renderImage
        ? renderImage(tokens, index, options, environment, renderer)
        : renderer.renderToken(tokens, index, options)
    }

    const renderLinkOpen = markdown.renderer.rules.link_open
    markdown.renderer.rules.link_open = (tokens, index, options, environment, renderer) => {
      const token = tokens[index]
      const target = token?.attrGet('href') ?? ''
      if (/^https?:\/\//i.test(target)) {
        token?.attrSet('target', '_blank')
        token?.attrSet('rel', 'noopener noreferrer')
        token?.attrSet('referrerpolicy', 'no-referrer')
      }
      return renderLinkOpen
        ? renderLinkOpen(tokens, index, options, environment, renderer)
        : renderer.renderToken(tokens, index, options)
    }
  },
})
