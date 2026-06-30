import {
  to = okta_group.source_admins
  id = "00gsourceadmins"
}

import {
  to = okta_app_oauth.customer_portal_oidc
  id = "0oasourceapp1"
}

import {
  to = okta_trusted_origin.customer_portal_origin
  id = "toresourcetrusted1"
}

import {
  to = okta_network_zone.corporate_vpn
  id = "nzsourcecorp"
}

import {
  to = okta_auth_server.default
  id = "ausdefault123"
}

import {
  to = okta_auth_server_scope.ausdefault123_openid
  id = "ausdefault123/scpopenid"
}

import {
  to = okta_auth_server_scope.ausdefault123_profile
  id = "ausdefault123/scpprofile"
}

import {
  to = okta_auth_server_claim.ausdefault123_tenant_id
  id = "ausdefault123/clmtenant"
}

import {
  to = okta_auth_server_policy.ausdefault123_default_policy
  id = "ausdefault123/poldefault"
}

import {
  to = okta_auth_server_policy_rule.ausdefault123_poldefault_default_rule
  id = "ausdefault123/poldefault/ruldefault"
}

import {
  to = okta_policy_signon.okta_sign_on_default_policy
  id = "00psignon"
}

import {
  to = okta_policy_password.password_default_password_policy
  id = "00ppassword"
}

import {
  to = okta_idp_saml.corporate_saml_idp
  id = "0oaidpsaml"
}
