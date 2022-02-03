# homeassistant-sbicrypto-pool

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

# SBICrypto Pool

### Installation with HACS
---
- Make sure that [HACS](https://hacs.xyz/) is installed
- Add the URL for this repository as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories) in HACS
- Install via `HACS -> Integrations`

### Usage
---
In order to use this integration, you need to first [Register an account with SBICrypto](https://sbicrypto.com), and then [generate an API key](https://pool.sbicrypto.com/api-access) from the "API Access" settings section.

To use this component in your installation, add the following to your `configuration.yaml` file:

```yaml
sbicrypto_pool:
  api_key: !secret sbicrypto_api_key
  api_secret: !secret sbicrypto_api_secret
```

#### Configuration variables:
| Key               | Type   | Required | Description                               | Default |
| :---------------- | :----: | :------: |:--------------------------------------    | :-----: |
| `name`            | string | No       | Name for the created sensors              | SBICrypto |
| `api_key`         | string | Yes      | SBICrypto API key                         | -       |
| `api_secret`      | string | Yes      | SBICrypto API secret                      | -       |
| `miners`          | array  | No       | List of pool accounts                     | -       |

#### Full example configuration
```yaml
sbicrypto_pool:
  name: My SBICrypto
  api_key: !secret sbicrypto_api_key
  api_secret: !secret sbicrypto_api_secret
  miners:
    - my_account
```

This configuration will create the following entities in your Home Assistant instance:
- Status sensors for each account, as example:
  - "My SBICrypto my_account status" (`sensor.my_sbicrypto_my_account_status`)
- Worker's sensors for each bundle (account + algo + worker)> as example
  - "My SBICrypto my_account.1023 worker" (`sensor.my_sbicrypto_my_account_1023_worker`)

### Configuration details
---

#### `name`
The `name` you specify will be used as a prefix for all the sensors this integration creates. By default, the prefix is simply "SBICrypto".

#### `api_key` and `api_secret`
An API key and secret from SBICrypto are **required** for this integration to function.  It is *highly recommended* to store your API key and secret in Home Assistant's `secrets.yaml` file.

#### `miners`
A list of pool accounts can be specified here


## Donate

if You like this component - feel free to donate me

* BTC: 1ALWfyhkniqZjLzckS2GDKmQXvEnzvDfth 
* ETH: 0xef89238d7a30694041e64e31b7991344e618923f
* LTC: LeHu1RaJhjH6bsoiqtEwZoZg6K6qeorsRf
* USDT: TFLt756zrKRFcvhSkjSWaXkfEzhv2M55YN
