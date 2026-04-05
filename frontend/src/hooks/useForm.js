import { useState, useCallback } from 'react'

const VALIDATORS = {
  required: (v) =>
    !v || v.toString().trim() === '' ? 'This field is required' : null,
  email: (v) =>
    v && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) ? 'Invalid email address' : null,
  minLength: (min) => (v) =>
    v && v.length < min ? `Minimum ${min} characters required` : null,
  pattern: (regex, msg) => (v) =>
    v && !regex.test(v) ? msg || 'Invalid format' : null,
}

/**
 * useForm — custom form state hook
 *
 * validationRules shape:
 *   { fieldName: ['required', 'email', { type: 'minLength', value: 8 }, customFn] }
 */
export default function useForm(initialValues, validationRules = {}) {
  const [values, setValues] = useState(initialValues)
  const [errors, setErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  const validateFields = useCallback(
    (fieldValues = values) => {
      const newErrors = {}
      for (const field in validationRules) {
        const rules = validationRules[field]
        for (const rule of rules) {
          let error = null
          if (typeof rule === 'string') {
            error = VALIDATORS[rule]?.(fieldValues[field]) ?? null
          } else if (typeof rule === 'function') {
            error = rule(fieldValues[field])
          } else if (rule?.type === 'minLength') {
            error = VALIDATORS.minLength(rule.value)(fieldValues[field])
          } else if (rule?.type === 'pattern') {
            error = VALIDATORS.pattern(rule.value, rule.message)(fieldValues[field])
          }
          if (error) {
            newErrors[field] = error
            break
          }
        }
      }
      return newErrors
    },
    [values, validationRules]
  )

  const handleChange = useCallback(
    (e) => {
      const { name, value, type, checked } = e.target
      const newVal = type === 'checkbox' ? checked : value
      setValues((prev) => ({ ...prev, [name]: newVal }))
      if (errors[name]) {
        setErrors((prev) => {
          const next = { ...prev }
          delete next[name]
          return next
        })
      }
    },
    [errors]
  )

  const handleSubmit = useCallback(
    (onSubmit) => async (e) => {
      e.preventDefault()
      const newErrors = validateFields()
      if (Object.keys(newErrors).length > 0) {
        setErrors(newErrors)
        return
      }
      setIsSubmitting(true)
      try {
        await onSubmit(values)
      } finally {
        setIsSubmitting(false)
      }
    },
    [values, validateFields]
  )

  const reset = useCallback(() => {
    setValues(initialValues)
    setErrors({})
  }, [initialValues])

  const setFieldValue = useCallback((name, value) => {
    setValues((prev) => ({ ...prev, [name]: value }))
  }, [])

  return { values, errors, handleChange, handleSubmit, isSubmitting, reset, setValues, setFieldValue }
}
