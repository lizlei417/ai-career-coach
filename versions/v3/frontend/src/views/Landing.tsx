import {useApp} from '../lib/store'
import {LangSwitch} from '../components/ui'
import {LandingPage} from './LandingPage'
export {Logo} from './LandingPage'
export default function Landing(){const {t,enter}=useApp();return <LandingPage t={t} enter={enter} languageControl={<LangSwitch/>}/>}
