import { describe, expect, it } from 'vitest'
import { isAllowedPublicImageUrl } from './markdown'

describe('isAllowedPublicImageUrl', () => {
  it('accepts only HTTPS image locations', () => {
    expect(isAllowedPublicImageUrl('https://images.example.com/label.jpg')).toBe(true)
    expect(isAllowedPublicImageUrl('HTTPS://images.example.com/label.webp')).toBe(true)
    expect(isAllowedPublicImageUrl('http://images.example.com/label.jpg')).toBe(false)
    expect(isAllowedPublicImageUrl('data:image/png;base64,abc')).toBe(false)
    expect(isAllowedPublicImageUrl('javascript:alert(1)')).toBe(false)
    expect(isAllowedPublicImageUrl('/local/image.png')).toBe(false)
    expect(isAllowedPublicImageUrl('https://')).toBe(false)
    expect(isAllowedPublicImageUrl('https://user:secret@images.example.com/label.jpg')).toBe(false)
  })
})
