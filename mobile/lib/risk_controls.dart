import 'package:flutter/material.dart';
import 'api.dart';
class RiskControls extends StatefulWidget {
 final Api api;const RiskControls({super.key,required this.api});
 @override State<RiskControls> createState()=>_RiskControlsState();
}
class _RiskControlsState extends State<RiskControls>{
 Map<String,dynamic>? limits;String? error;bool busy=false;
 @override void initState(){super.initState();load();}
 Future<void> load()async{try{final data=await widget.api.call('/risk');if(mounted)setState(()=>limits=Map<String,dynamic>.from(data));}catch(e){if(mounted)setState(()=>error=e.toString());}}
 @override Widget build(BuildContext context)=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
 const Text('Conservative demo risk controls'),if(error!=null)Text(error!),if(limits==null)TextButton(onPressed:load,child:const Text('Load risk settings')),
 if(limits!=null)...[
 for(final item in [('per_trade','Risk per trade',.01),('daily_loss','Daily loss budget',.03),('drawdown','Maximum drawdown',.10)])...[
 Text('${item.$2}: ${((limits![item.$1] as num)*100).toStringAsFixed(1)}%'),Slider(value:(limits![item.$1] as num).toDouble(),min:.001,max:item.$3,onChanged:(v)=>setState(()=>limits![item.$1]=v)),],
 const Text('Hard caps: 1 position, 3 consecutive losses, 10 trades per day. Settings cannot exceed server caps.'),
 FilledButton(onPressed:busy?null:()async{setState(()=>busy=true);try{await widget.api.call('/risk',body:limits!);if(mounted)setState(()=>error='Risk settings saved');}catch(e){if(mounted)setState(()=>error=e.toString());}finally{if(mounted)setState(()=>busy=false);}},child:const Text('Save risk limits')),
 ]]);
}
